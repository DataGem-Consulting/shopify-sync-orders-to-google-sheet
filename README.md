# Shopify Orders to Google Sheets Sync

## Overview

This Flask-based web application is designed to synchronize Shopify order data with Google Sheets. It automatically fetches orders from a Shopify store, parses them into a structured format, and organizes them into separate Google Sheets for each month. This provides an easy and automated way for non-technical users to view and analyze order data.

The application is containerized using Docker and is configured for deployment on Google Cloud Run.

## Features

*   **Automated Order Sync:** Fetches orders from the Shopify API.
*   **Monthly Organization:** Creates and manages a separate Google Sheet for each month's orders (e.g., "Commandes 2025-04") within a designated Google Drive folder.
*   **Real-time Updates:** Supports real-time order pushing via a webhook endpoint (`/push_order`), ideal for integrating with Shopify's order creation webhooks.
*   **Bulk Reset/Resync:** Provides an endpoint (`/reset_all_sheets`) to perform a full resynchronization, clearing all existing sheets in the target folder and repopulating them with historical data from a specified date range.
*   **Duplicate Prevention:** Checks for existing order IDs (`N° commande`) before appending a new order to prevent duplicate entries.
*   **Containerized & Cloud-Ready:** Includes a `Dockerfile` and `cloudbuild.yaml` for seamless deployment on Google Cloud Run or other container-based platforms.

## Configuration

The application is configured using environment variables. For local development, you can create a `.env` file in the root directory. For production, these variables should be set in your deployment environment (e.g., Cloud Run service configuration).

### Environment Variables

*   `DRIVE_FOLDER_ID`: The ID of the Google Drive folder where the monthly Google Sheets will be created and stored.
*   `SERVICE_ACCOUNT_FILE`: A JSON string containing the Google Cloud Service Account credentials required to access Google Drive and Google Sheets APIs.
*   `SHOPIFY_CREDENTIALS`: A JSON string containing the Shopify private app credentials.

### Example `.env` file

```env
DRIVE_FOLDER_ID="your_google_drive_folder_id"
SERVICE_ACCOUNT_FILE='{"type": "service_account", "project_id": "...", ...}'
SHOPIFY_CREDENTIALS='{"shopify": {"API_KEY": "...", "API_TOKEN": "shpat_...", "MERCHANT": "your-store-name", "VERSION": "2025-07"}}'
```

**Note:** The `var/` directory can also be used to store `shopify_credentials.json` and `bigquery_service_account.json` for local development, but this is not recommended for production. The `.gitignore` file correctly excludes this directory.

## API Endpoints

### `GET /health`

A simple health check endpoint to verify that the application is running.

**Response (200 OK):**
```json
{
  "status": "healthy"
}
```

### `GET /reset_all_sheets`

This endpoint fetches all orders from Shopify within a specified date range, completely empties the designated Google Drive folder, and then creates new Google Sheets for each month, populating them with the fetched order data. This is useful for a complete data refresh.

**Query Parameters:**

*   `password` (required)
*   `updated_at_min` (optional): The start date for fetching orders in `YYYY-MM-DDTHH:MM:SSZ` format. Defaults to `2025-04-01T00:00:00Z`.
*   `updated_at_max` (optional): The end date for fetching orders in `YYYY-MM-DDTHH:MM:SSZ` format. Defaults to the current datetime.

**Example Request:**
`GET /reset_all_sheets?updated_at_min=2025-05-01T00:00:00Z&updated_at_max=2025-05-31T23:59:59Z`

**Success Response (200 OK):**
```json
{
  "message": "All sheets reset and orders processed successfully"
}
```

**Error Response (500 Internal Server Error):**
```json
{
  "error": "Failed to reset all sheets"
}
```

### `POST /push_order`

This endpoint receives a single Shopify order payload (typically from a Shopify webhook) and appends it as a new row to the appropriate monthly Google Sheet.

*   It determines the correct sheet based on the order's `created_at` date.
*   If a sheet for that month does not exist, it creates one automatically.
*   It checks if the order ID already exists in the sheet to prevent duplicates.

**Request Body:**

The request body should be a JSON object representing a Shopify order. The application will parse this object to extract the relevant fields. The full Shopify order payload is expected.

**Example Shopify Order Payload (Partial):**
```json
{
    "id": 1234567890123,
    "email": "customer@example.com",
    "created_at": "2025-04-15T16:05:47-04:00",
    "total_price": "59.99",
    "total_line_items_price": "49.99",
    "total_discounts": "0.00",
    "total_shipping_price_set": {
        "shop_money": {
            "amount": "10.00",
            "currency_code": "USD"
        }
    },
    "currency": "USD",
    "customer": {
        "id": 9876543210987
    },
    "shipping_address": {
        "address1": "123 Shopify St",
        "city": "Ottawa",
        "country": "Canada"
    },
    "line_items": [
        {
            "title": "Awesome T-Shirt",
            "quantity": 1,
            "price": "49.99",
            "price_set": {
                "shop_money": {
                    "amount": "49.99",
                    "currency_code": "USD"
                }
            }
        }
    ]
}
```

**Success Response (200 OK):**
```json
{
  "message": "Order pushed successfully"
}
```

**Error Response (500 Internal Server Error):**
```json
{
  "error": "Failed to push order"
}
```
