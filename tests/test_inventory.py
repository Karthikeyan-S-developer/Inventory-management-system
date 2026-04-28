import unittest
from inventory_system import (InventoryEntityFactory,MovementType,Role,Warehouse)
class InventoryTests(unittest.TestCase):
    def setUp(self):
        self.warehouse=Warehouse("W1","Central","Mumbai")
        self.supplier=InventoryEntityFactory.create_supplier(
            "S1",
            "ABC Supplies",
            "+911234567890",
            "contact@abc.com",
            5,
            ["SKU1"],
        )
        self.product = InventoryEntityFactory.create_product(
            "SKU1",
            "Notebook",
            "Office",
            "pcs",
            10,
            8,
            "S1",
        )
        self.warehouse.registerSupplier(self.supplier)
        self.warehouse.registerProduct(self.product)

    def test_create_product_and_order_item(self):
        item = InventoryEntityFactory.create_order_item("SKU1", 2)
        self.assertEqual(item.sku, "SKU1")
        self.assertEqual(item.quantity, 2)

    def test_trigger_reorder_and_stock_receive(self):
        orders = self.warehouse.triggerReorder()
        self.assertEqual(len(orders), 1)
        po = orders[0]
        po.approve()
        po.send()
        self.warehouse.receiveGoods(po, [InventoryEntityFactory.create_order_item("SKU1", 5)], "STAFF1")
        self.assertEqual(self.product.currentStock, 13)

    def test_manager_adjustment_requires_role(self):
        with self.assertRaises(Exception):
            self.warehouse.adjustStock("SKU1", -1, "Damaged", "STAFF1", Role.WAREHOUSE_STAFF)
        self.warehouse.adjustStock("SKU1", -1, "Damaged", "MGR1", Role.STORE_MANAGER)
        self.assertEqual(self.product.currentStock, 7)


if __name__ == "__main__":
    unittest.main()
