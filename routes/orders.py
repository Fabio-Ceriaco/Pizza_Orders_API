from fastapi import APIRouter
from schemas.schemas import OrderCreate, OrderRead, ItemCreate
from sqlmodel import Session, select
from database.conn import get_session, Orders, Users, Items
from fastapi import Depends, HTTPException, status
from security.security import get_current_user
from uuid import UUID

orders_route = APIRouter(
    prefix="/orders", tags=["orders"], dependencies=[Depends(get_current_user)]
)


@orders_route.post("/", response_model=OrderRead)
async def create_order(order: OrderCreate, db: Session = Depends(get_session)):
    """
    Endpoint to create a new order in the database."""
    try:
        new_order = Orders.model_validate(order)
        db.add(new_order)
        db.commit()
        db.refresh(new_order)
        return new_order
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An error occurred while creating the order: {str(e)}",
        )


@orders_route.get("/cancel/{order_id}")
async def cancel_order(
    order_id: UUID,
    db: Session = Depends(get_session),
    current_user: Users = Depends(get_current_user),
):
    """
    Endpoint to cancel an existing order by its ID.
    """
    try:

        query = select(Orders).where(Orders.uid == order_id)
        order = db.exec(query).first()
        if not current_user.admin or order.user_uid != current_user.uid:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You do not have permission to cancel this order",
            )
        if not order:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Order not found"
            )
        order.status = "CANCELLED"

        db.commit()
        db.refresh(order)
        return {"message": f"Order {order_id} cancelled successfully!", "order": order}
    except Exception as e:
        return {"message": f"An error occurred while canceling the order: {str(e)}"}


@orders_route.get("/", response_model=list[OrderRead])
async def list_orders(
    db: Session = Depends(get_session),
    current_user: Users = Depends(get_current_user),
    offset: int = 0,
    limit: int = 20,
):
    """
    Endpoint to list all orders in the database.
    """
    if current_user.admin == False:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have permission to view all orders",
        )
    try:
        query = select(Orders).offset(offset).limit(limit)
        orders = db.exec(query).all()
        return orders
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An error occurred while fetching orders: {str(e)}",
        )


@orders_route.post("/add-item/{order_id}")
async def add_item_to_order(
    order_id: UUID,
    item: ItemCreate,
    db: Session = Depends(get_session),
    current_user: Users = Depends(get_current_user),
):
    """
    Endpoint to add an item to an existing order.
    """
    try:
        query = select(Orders).where(
            Orders.uid == order_id
        )  # Check if the order exists and if the user has permission to add items to it
        order = db.exec(query).first()
        if not order or order.status == "CANCELLED":  # Check if the order exists
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Order not found or is cancelled",
            )
        if (
            not current_user.admin or current_user.uid != order.user_uid
        ):  # Check if the user has permission to add items to the order
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You do not have permission to add items to this order",
            )

        item.order_uid = order_id  # Set the order_uid of the item to the order_id
        new_item = Items.model_validate(
            item
        )  # Create a new item instance from the ItemCreate schema
        db.add(new_item)  # Add the new item to the database session
        order.total += (
            item.unit_price * item.quantity
        )  # Update the total price of the order by adding the price of the new item
        db.commit()  # Commit the transaction to save the changes to the database
        db.refresh(order)  # Refresh the order instance to get the updated total price
        return {"message": f"Item added to order {order_id} successfully!"}
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An error occurred while adding item to the order: {str(e)}",
        )


@orders_route.delete("/remove-item/{item_id}")
async def remove_item_from_order(
    item_uid: UUID,
    db: Session = Depends(get_session),
    current_user: Users = Depends(get_current_user),
):
    """
    Endpoint to remove an item from an existing order.
    """
    try:
        query = select(Items).where(Items.uid == item_uid)
        item = db.exec(query).first()
        if not item:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Item not found"
            )
        order_query = select(Orders).where(Orders.uid == item.order_uid)
        order = db.exec(order_query).first()
        if not order or order.status == "CANCELLED":
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Order not found or is cancelled",
            )
        if not current_user.admin or current_user.uid != order.user_uid:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You do not have permission to remove items from this order",
            )
        order.total -= item.unit_price * item.quantity
        db.delete(item)
        db.commit()
        db.refresh(order)
        return {
            "message": f"Item {item_uid} removed from order {order.uid} successfully!"
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An error occurred while removing item from the order: {str(e)}",
        )


@orders_route.post("/complete/{order_id}", response_model=OrderRead)
async def complete_order(
    order_uid: UUID,
    db: Session = Depends(get_session),
    current_user: Users = Depends(get_current_user),
):
    """
    Endpoint to mark an order as completed.
    """
    try:
        query = select(Orders).where(Orders.uid == order_uid)
        order = db.exec(query).first()
        if not order:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Order not found"
            )
        if not current_user.admin or current_user.uid != order.user_uid:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You do not have permission to complete this order",
            )
        if order.status == "CANCELLED":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot complete a cancelled order",
            )
        order.status = "COMPLETED"
        db.commit()
        db.refresh(order)
        return order
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An error occurred while completing the order: {str(e)}",
        )


@orders_route.get("/user-orders", response_model=list[OrderRead])
async def get_orders_by_user(
    db: Session = Depends(get_session), current_user: Users = Depends(get_current_user)
):
    """
    Endpoint to get all orders for a specific user.
    """
    try:
        query = select(Orders).where(Orders.user_uid == current_user.uid)
        orders = db.exec(query).all()
        if not orders:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="No orders found for this user",
            )
        return orders
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An error occurred while fetching orders for the user: {str(e
        )}",
        )
