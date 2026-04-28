from inventory_system import InventoryEntityFactory, MovementType, Role, Warehouse

def prompt_int(prompt, default=None):
    while True:
        value = input(f"{prompt}{' [' + str(default) + ']' if default is not None else ''}: ").strip()
        if not value and default is not None:
            return default
        try:
            return int(value)
        except ValueError:
            print("Please enter a valid integer.")

def prompt_choice(prompt, options):
    for idx, option in enumerate(options, start=1):
        print(f"  {idx}. {option}")
    while True:
        choice = input(prompt).strip()
        try:
            num = int(choice)
            if 1 <= num <= len(options):
                return options[num - 1]
        except ValueError:
            pass
        print("Choose a valid option number.")

def main():
    warehouse = Warehouse("WH1", "Main Warehouse", "Mumbai")
    orders = []

    while True:
        print("\n=== Inventory Operations ===")
        print("1. Register supplier")
        print("2. Register product")
        print("3. Trigger reorder")
        print("4. Approve and send purchase order")
        print("5. Receive goods")
        print("6. Adjust stock")
        print("7. Show dashboard")
        print("8. Show product stock history")
        print("9. Show alerts")
        print("0. Exit")

        choice = input("Select action: ").strip()

        if choice == "0":
            print("Exiting inventory application.")
            break

        if choice == "1":
            supplier_id = input("Supplier ID: ").strip()
            name = input("Supplier name: ").strip()
            contact = input("Contact number: ").strip()
            email = input("Email: ").strip()
            lead_time = prompt_int("Lead time days", 3)
            supplier = InventoryEntityFactory.create_supplier(
                supplier_id,
                name,
                contact,
                email,
                lead_time,
                [],
            )
            warehouse.registerSupplier(supplier)
            print(f"Supplier '{supplier_id}' registered.")
            continue

        if choice == "2":
            sku = input("Product SKU: ").strip()
            name = input("Product name: ").strip()
            category = input("Category: ").strip()
            unit = input("Unit: ").strip()
            reorder_level = prompt_int("Reorder level", 10)
            current_stock = prompt_int("Current stock", 0)
            supplier_id = input("Supplier ID: ").strip()
            product = InventoryEntityFactory.create_product(
                sku,
                name,
                category,
                unit,
                reorder_level,
                current_stock,
                supplier_id,
            )
            warehouse.registerProduct(product)
            print(f"Product '{sku}' registered.")
            continue

        if choice == "3":
            orders = warehouse.triggerReorder()
            if not orders:
                print("No reorder required at this time.")
            else:
                for idx, order in enumerate(orders, start=1):
                    print(f"{idx}. PO ID: {order.po_id}, Supplier: {order.supplier_id}, Status: {order.status}")
            continue

        if choice == "4":
            if not orders:
                print("No purchase orders available.")
                continue
            for idx, order in enumerate(orders, start=1):
                print(f"{idx}. {order.po_id} - {order.status}")
            selected = prompt_int("Select PO number", 1)
            if selected < 1 or selected > len(orders):
                print("Invalid order selection.")
                continue
            order = orders[selected - 1]
            order.approve()
            order.send()
            print(f"Purchase order {order.po_id} approved and sent.")
            continue

        if choice == "5":
            if not orders:
                print("No purchase orders available.")
                continue
            for idx, order in enumerate(orders, start=1):
                print(f"{idx}. {order.po_id} - {order.status}")
            selected = prompt_int("Select PO number", 1)
            if selected < 1 or selected > len(orders):
                print("Invalid order selection.")
                continue
            order = orders[selected - 1]
            sku = input("Received SKU: ").strip()
            quantity = prompt_int("Received quantity", 0)
            staff_id = input("Staff ID: ").strip() or "STAFF1"
            receipt = warehouse.receiveGoods(order, [InventoryEntityFactory.create_order_item(sku, quantity)], staff_id)
            print(f"Goods received recorded with GRN {receipt.grn_id}.")
            continue

        if choice == "6":
            sku = input("Product SKU: ").strip()
            quantity = prompt_int("Adjustment quantity (use negative for reduction)", 0)
            reason = input("Reason: ").strip()
            role = prompt_choice("Choose role: ", ["Store Manager", "Warehouse Staff", "Supplier"])
            try:
                warehouse.adjustStock(sku, quantity, reason, "MANAGER", role)
                print("Stock adjusted successfully.")
            except Exception as exc:
                print(f"Adjustment failed: {exc}")
            continue

        if choice == "7":
            dashboard = warehouse.getDashboard()
            print("Dashboard:")
            for key, value in dashboard.items():
                print(f"  {key}: {value}")
            continue

        if choice == "8":
            sku = input("Product SKU: ").strip()
            try:
                history = warehouse.lookupProduct(sku).get_stock_history()
                print(f"Stock history for {sku}:")
                for movement in history:
                    print(f"  {movement.timestamp} - {movement.type} {movement.quantity} - {movement.reason}")
            except Exception as exc:
                print(f"Unable to show history: {exc}")
            continue

        if choice == "9":
            alerts = warehouse.getAlerts()
            print("Alerts:")
            if not alerts:
                print("  No alerts.")
            for alert in alerts:
                print(f"  {alert}")
            continue

        print("Unknown option. Please choose a valid action.")

if __name__ == "__main__":
    main()
