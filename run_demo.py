from inventory_system import InventoryEntityFactory,MovementType,Role,Warehouse

def main()->None:
    warehouse=Warehouse("W1","Central","Mumbai")
    supplier=InventoryEntityFactory.create_supplier(
        "S1",
        "ABC Supplies",
        "+911234567890",
        "contact@abc.com",
        5,
        ["SKU1"],
    )
    product=InventoryEntityFactory.create_product(
        "SKU1",
        "Notebook",
        "Office",
        "pcs",
        10,
        8,
        "S1",
    )
    warehouse.registerSupplier(supplier)
    warehouse.registerProduct(product)

    print("Initial dashboard:",warehouse.getDashboard())
    orders=warehouse.triggerReorder()
    print("Generated purchase orders:",[o.poId for o in orders])

    if orders:
        po=orders[0]
        po.approve()
        po.send()
        warehouse.receiveGoods(po,[InventoryEntityFactory.create_order_item("SKU1",5)],"STAFF1")
        print("Stock after receive:",warehouse.lookupProduct("SKU1").currentStock)

    warehouse.adjustStock("SKU1",-1,"Damaged good","MGR1",Role.STORE_MANAGER)
    print("Stock after adjustment:",warehouse.lookupProduct("SKU1").currentStock)


if __name__=="__main__":
    main()
