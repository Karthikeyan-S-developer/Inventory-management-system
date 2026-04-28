from __future__ import annotations
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from enum import Enum
from typing import List,Tuple
class InventoryError(Exception):
    pass
class ProductNotFoundError(InventoryError):
    pass
class DuplicateGRNError(InventoryError):
    pass
class InsufficientPrivilegesError(InventoryError):
    pass
class InvalidOperationError(InventoryError):
    pass
class NegativeStockError(InventoryError):
    pass
class MovementType(Enum):
    RECEIPT=(False,"Receipt")
    SALE=(False,"Sale")
    ADJUSTMENT=(True,"Adjustment")
    RETURN=(False,"Return")
    WRITE_OFF=(True,"Write-off")
    TRANSFER=(False,"Transfer")

    def __init__(self, requires_approval:bool,label:str):
        self._requires_approval=requires_approval
        self.label=label

    @property
    def requires_approval(self)->bool:
        return self._requires_approval

class PurchaseOrderStatus(Enum):
    DRAFT="Draft"
    APPROVED="Approved"
    SENT="Sent"
    RECEIVED="Received"
    CANCELED="Canceled"

class Role(Enum):
    STORE_MANAGER="Store Manager"
    WAREHOUSE_STAFF="Warehouse Staff"
    SUPPLIER="Supplier"

@dataclass(frozen=True)
class OrderItem:
    sku:str
    quantity:int

    def __post_init__(self)->None:
        if not self.sku.strip():
            raise ValueError("SKU must be provided")
        if self.quantity<=0:
            raise ValueError("Quantity must be positive")

@dataclass(frozen=True)
class Discrepancy:
    sku:str
    expected_quantity:int
    received_quantity:int
    reason:str

    def __post_init__(self)->None:
        if not self.reason.strip():
            raise ValueError("Discrepancy reason must be provided")

class StockMovement:
    _audit_trail:List["StockMovement"]=[]

    def __init__(self,sku:str,movement_type:MovementType,quantity:int,reason:str|None,staff_id:str|None):
        if not sku.strip():
            raise ValueError("SKU must be provided")
        if quantity==0:
            raise ValueError("Quantity cannot be zero")
        self.movementId=str(uuid.uuid4())
        self.sku=sku
        self.type=movement_type
        self.quantity=quantity
        self.reason=reason
        self.staffId=staff_id
        self.timestamp=datetime.now(timezone.utc)

    def log(self)->None:
        StockMovement._audit_trail.append(self)

    @classmethod
    def getAuditTrail(cls)->Tuple["StockMovement",...]:
        return tuple(cls._audit_trail)

@dataclass
class Product:
    sku:str
    name:str
    category:str
    unit:str
    reorderLevel:int
    currentStock:int
    supplierId:str

    def __post_init__(self)->None:
        if not self.sku.strip():
            raise ValueError("SKU must be provided")
        if self.reorderLevel<0:
            raise ValueError("Reorder level cannot be negative")
        if self.currentStock<0:
            raise ValueError("Current stock cannot be negative")

    def isLowStock(self)->bool:
        return self.currentStock<=self.reorderLevel

    def updateStock(self,quantity:int,movement_type:MovementType,reason:str|None=None,staff_id:str|None=None)->None:
        if movement_type.requires_approval and not reason:
            raise InvalidOperationError("Reason required for approval movement")
        if self.currentStock + quantity<0:
            raise NegativeStockError("Stock cannot become negative")
        StockMovement(self.sku,movement_type,quantity,reason,staff_id).log()
        self.currentStock+=quantity

    def getStockHistory(self)->List[StockMovement]:
        return [m for m in StockMovement.getAuditTrail() if m.sku==self.sku]

class Supplier:
    def __init__(self,supplierId:str,name:str,contact:str,email:str,leadTimeDays:int,products:list[str]|None=None):
        self.supplierId=supplierId
        self.name=name
        self.contact=contact
        self.email=email
        self.leadTimeDays=leadTimeDays
        self.products=products or []
        self._delivery_history:List[GoodsReceived]=[]

    def createPO(self,items:list[OrderItem])->"PurchaseOrder":
        return PurchaseOrder(self.supplierId,items)

    def getDeliveryHistory(self)->List["GoodsReceived"]:
        return list(self._delivery_history)

    def record_delivery(self,goods_received:"GoodsReceived")->None:
        self._delivery_history.append(goods_received)

class GoodsReceived:
    def __init__(self,poId:str,receivedItems:list[OrderItem],staffId:str):
        self.grnId=str(uuid.uuid4())
        self.poId=poId
        self.receivedItems=receivedItems
        self.receivedDate=datetime.now(timezone.utc)
        self.staffId=staffId
        self.discrepancies:List[Discrepancy]=[]
        self.closed=False

    def record(self)->None:
        self.closed=True

    def flagDiscrepancy(self,expected_quantity:int,received_quantity:int,reason:str)->None:
        self.discrepancies.append(Discrepancy(self.receivedItems[0].sku if self.receivedItems else "", expected_quantity,received_quantity,reason))

    def close(self)->None:
        self.closed=True

class PurchaseOrder:
    def __init__(self,supplierId:str,items:list[OrderItem]):
        if not items:
            raise ValueError("Purchase order must contain at least one item")
        self.poId=str(uuid.uuid4())
        self.supplierId=supplierId
        self.items=items
        self.status=PurchaseOrderStatus.DRAFT
        self.createdDate=datetime.now(timezone.utc)
        self.approvedDate:datetime|None=None

    def approve(self)->None:
        if self.status!=PurchaseOrderStatus.DRAFT:
            raise InvalidOperationError("Only draft PO can be approved")
        self.status=PurchaseOrderStatus.APPROVED
        self.approvedDate=datetime.now(timezone.utc)

    def send(self)->None:
        if self.status!=PurchaseOrderStatus.APPROVED:
            raise InvalidOperationError("PO must be approved before sending")
        self.status=PurchaseOrderStatus.SENT

    def receive(self,received_items:list[OrderItem],staff_id:str)->GoodsReceived:
        if self.status not in {PurchaseOrderStatus.APPROVED,PurchaseOrderStatus.SENT}:
            raise InvalidOperationError("PO must be approved or sent before receiving")
        self.status=PurchaseOrderStatus.RECEIVED
        return GoodsReceived(self.poId,received_items,staff_id)

    def cancel(self)->None:
        if self.status==PurchaseOrderStatus.RECEIVED:
            raise InvalidOperationError("Cannot cancel a received PO")
        self.status=PurchaseOrderStatus.CANCELED

class Warehouse:
    def __init__(self,warehouseId:str,name:str,location:str):
        self.warehouseId=warehouseId
        self.name=name
        self.location=location
        self.products:dict[str,Product]={}
        self.suppliers:dict[str,Supplier]={}
        self.zones:list[str]=[]
        self.alerts:list[str]=[]
        self._recorded_grns:set[str]=set()

    def registerProduct(self,product:Product)->None:
        self.products[product.sku]=product

    def registerSupplier(self,supplier:Supplier)->None:
        self.suppliers[supplier.supplierId]=supplier

    def getDashboard(self)->dict:
        low_stock=[p.sku for p in self.products.values() if p.isLowStock()]
        return {
            "warehouseId":self.warehouseId,
            "name":self.name,
            "location":self.location,
            "total_products":len(self.products),
            "low_stock_count":len(low_stock),
            "low_stock_skus":low_stock,
            "alerts":list(self.alerts),
        }

    def triggerReorder(self)->list[PurchaseOrder]:
        orders:list[PurchaseOrder]=[]
        for product in self.products.values():
            if product.isLowStock():
                supplier=self.suppliers.get(product.supplierId)
                if not supplier:
                    self.alerts.append(f"Supplier {product.supplierId} not registered for {product.sku}")
                    continue
                qty=max(product.reorderLevel*2-product.currentStock,1)
                po=supplier.createPO([OrderItem(product.sku,qty)])
                orders.append(po)
                self.alerts.append(f"Reorder generated for {product.sku}")
        return orders

    def getAlerts(self)->list[str]:
        return list(self.alerts)

    def receiveGoods(self,purchase_order:PurchaseOrder,received_items:list[OrderItem],staff_id:str)->GoodsReceived:
        if purchase_order.poId in self._recorded_grns:
            raise DuplicateGRNError("GRN already recorded for this PO")
        grn=purchase_order.receive(received_items, staff_id)
        for item in received_items:
            self.updateStock(item.sku,item.quantity,MovementType.RECEIPT,"Goods received",staff_id)
        self._recorded_grns.add(purchase_order.poId)
        return grn

    def adjustStock(self,sku:str,quantity:int,reason:str,staff_id:str,role:Role)->None:
        if quantity<0 and role!=Role.STORE_MANAGER:
            raise InsufficientPrivilegesError("Only store manager can reduce stock")
        if sku not in self.products:
            raise ProductNotFoundError("Product SKU not recognized")
        self.products[sku].updateStock(quantity,MovementType.ADJUSTMENT,reason,staff_id)

    def updateStock(self,sku:str,quantity:int,movement_type:MovementType,reason:str|None,staff_id:str|None)->None:
        if sku not in self.products:
            raise ProductNotFoundError("Product SKU not recognized")
        self.products[sku].updateStock(quantity,movement_type,reason,staff_id)

    def lookupProduct(self,sku:str)->Product:
        if sku not in self.products:
            raise ProductNotFoundError("Product SKU not recognized")
        return self.products[sku]

class InventoryEntityFactory:
    @staticmethod
    def create_product(sku:str,name:str,category:str,unit:str, reorderLevel: int,currentStock:int, supplierId: str) -> Product:
        return Product(sku,name,category,unit,reorderLevel,currentStock,supplierId)

    @staticmethod
    def create_supplier(supplierId: str, name: str, contact: str, email: str, leadTimeDays: int, products: list[str] | None = None) -> Supplier:
        return Supplier(supplierId, name, contact, email, leadTimeDays,products)

    @staticmethod
    def create_order_item(sku: str, quantity:int)->OrderItem:
        return OrderItem(sku, quantity)

    @staticmethod
    def create_purchase_order(supplierId: str, items: list[OrderItem]) -> PurchaseOrder:
        return PurchaseOrder(supplierId, items)

    @staticmethod
    def create_goods_received(poId: str, receivedItems: list[OrderItem], staffId: str) -> GoodsReceived:
        return GoodsReceived(poId, receivedItems, staffId)

__all__ = ["OrderItem","Discrepancy","StockMovement","Product","Supplier","GoodsReceived","PurchaseOrder","Warehouse","InventoryEntityFactory","MovementType","PurchaseOrderStatus","Role","ProductNotFoundError","DuplicateGRNError","InsufficientPrivilegesError","InvalidOperationError","NegativeStockError","InventoryError"]
