import openpyxl
from openpyxl import Workbook

def create_excel():
    wb = Workbook()
    ws = wb.active
    ws.title = "Products Catalog"
    
    headers = ["Product ID", "Product Name", "Category", "Price (USD)", "Description", "Stock Status"]
    ws.append(headers)
    
    data = [
        ["LUM-100", "Lumiere V-Sync Smart Ring", "Wearables", 299.99, "Premium titanium smart ring tracking heart rate, HRV, blood oxygen, and detailed sleep stages.", "In Stock"],
        ["LUM-101", "Lumiere Core Band", "Wearables", 149.99, "Entry-level fitness band with 14-day battery life, step tracking, and basic heart rate monitoring.", "In Stock"],
        ["LUM-200", "Lumiere Smart Scale Pro", "Home Health", 129.99, "Wi-Fi connected body composition scale measuring weight, body fat %, muscle mass, and water weight.", "Out of Stock"],
        ["LUM-300", "Lumiere Health App Premium", "Software", 9.99, "Monthly subscription unlocking advanced AI insights, personalized coaching, and historical data export.", "Active"],
        ["LUM-105", "V-Sync Ring Charger", "Accessories", 39.99, "Replacement magnetic charging dock for the V-Sync Smart Ring.", "In Stock"],
        ["LUM-250", "Lumiere BP Monitor", "Home Health", 89.99, "FDA-cleared upper arm blood pressure monitor with Bluetooth syncing.", "Low Stock"]
    ]
    
    for row in data:
        ws.append(row)
        
    wb.save("data/products.xlsx")
    print("products.xlsx created successfully.")

if __name__ == "__main__":
    create_excel()
