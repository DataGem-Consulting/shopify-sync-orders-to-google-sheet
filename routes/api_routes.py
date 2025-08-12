from flask import json, request, jsonify, Blueprint
from config import Config
from flask_cors import cross_origin 
import traceback
import datetime 
from utils.shopifyHandler import ShopifyHandler
from utils.driveHandler import DriveHandler
from dotenv import load_dotenv
import os 
import pandas as pd

load_dotenv()

api_routes = Blueprint('apiRoutes', __name__)
config = Config()

driveHandler = DriveHandler()
shopifyHandler = ShopifyHandler()

api_routes.route('/health', methods=['GET'])
@cross_origin()
def health_check():
    return jsonify({"status": "healthy"}), 200

@api_routes.route('/reset_all_sheets', methods=['GET'])
@cross_origin()
def reset_all_sheets():
    try:

        password = request.headers.get('password')
        fake_insertion = request.args.get('fake_insertion', 'false').lower() == 'true'
        print(f"Fake insertion: {fake_insertion}")
        
        if password != os.getenv('RESET_PASSWORD'):
            return jsonify({"error": "Invalid password"}), 403
        
        print("Fetching orders from Shopify")
        orders = shopifyHandler.getOrders(start_time=request.args.get('updated_at_min', "2025-04-01T00:00:00Z"),
                                         end_time=request.args.get('updated_at_max', datetime.datetime.now().strftime('%Y-%m-%dT%H:%M:%S%z')))
        print(f"Fetched {len(orders)} orders from Shopify")
        folderId = os.environ.get('DRIVE_FOLDER_ID')
        driveHandler.emptyFolder(folderId)
        print(f"Folder {folderId} emptied successfully")
        classified_orders = {}

        for order in orders:
            created_at = order.get('created_at')
            created_at = datetime.datetime.strptime(created_at, '%Y-%m-%dT%H:%M:%S%z')
            month = created_at.strftime('%Y-%m')
            
            classified_orders.setdefault(month, []).append(shopifyHandler.parse_order(order, fake_insertion=fake_insertion))

        # Process classified orders
        for month, orders in classified_orders.items():
            # Create a new Google Sheet for the month
            print(f"Creating sheet for month: {month} with {len(orders)} orders")
            sheet_id = driveHandler.createSheetInFolder(f"Commandes {month}", folderId)
            if not sheet_id:
                traceback.print_exc()
                return jsonify({"error": f"Failed to create sheet for month {month}"}), 500
            # Write orders to the Google Sheet
            orders_df = pd.DataFrame(orders)
            driveHandler.googleSheetHandler.writeData(sheet_id, orders_df)
        return jsonify({"message": "All sheets reset and orders processed successfully"}), 200
    
    except Exception as e:
        traceback.print_exc()
        return jsonify({"error": "Failed to reset all sheets"}), 500

@api_routes.route('/push_order', methods=['POST'])
@cross_origin()
def push_order():
    try:
        if request.headers.get('x-shopify-shop-domain') != os.getenv('SHOPIFY_ACCEPTED_URL'):
            return jsonify({"error": "Invalid shop domain"}), 403

        order_data = request.json
        
        created_at = order_data.get('created_at')
        created_at = datetime.datetime.strptime(created_at, '%Y-%m-%dT%H:%M:%S%z')
        month = created_at.strftime('%Y-%m')
        folderId = os.environ.get('DRIVE_FOLDER_ID')

        files = driveHandler.getFiles(folderId)

        order_data = shopifyHandler.parse_order(order_data)

        if "Commandes " + month not in [file['name'] for file in files]:
            print(f"Creating new sheet for month: {month}")
            sheet_id = driveHandler.createSheetInFolder(f"Commandes {month}", folderId)
            driveHandler.googleSheetHandler.append_to_sheet(sheet_id, order_data, is_first_row=True)
        else:
            print(f"Appending to existing sheet for month: {month}")
            sheet_id = next(file['id'] for file in files if file['name'] == f"Commandes {month}")
            print(f"Sheet ID: {sheet_id}")

            orders_in_sheet = driveHandler.googleSheetHandler.getSheetData(sheet_id, 'Sheet1!A1:Z1000')
            
            if orders_in_sheet.empty:
                print("Sheet is empty, adding headers")
                driveHandler.googleSheetHandler.append_to_sheet(sheet_id, order_data, is_first_row=True)
                return jsonify({"message": "Order pushed successfully"}), 200
            if any(order['N° commande'] == order_data['N° commande'] for order in orders_in_sheet.to_dict(orient='records')):
                print("Order already exists in the sheet")
                return jsonify({"message": "Order already exists in the sheet"}), 200

            driveHandler.googleSheetHandler.append_to_sheet(sheet_id, order_data)
            print("Order pushed successfully")
        return jsonify({"message": "Order pushed successfully"}), 200
    except Exception as e:
        traceback.print_exc()
        return jsonify({"error": "Failed to push order"}), 500
