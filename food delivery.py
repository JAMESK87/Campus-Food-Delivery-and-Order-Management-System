"""
Campus Food Delivery and Order Management System
---------------------------------------------------
A menu-driven console application that lets a canteen take digital
orders instead of relying on shouted orders and handwritten tickets.

Author: [Bamwesigye Ronnie, Basemera Hilda,Khathindi James, Nansikombi Lillian, Nalwanga sarah, Kato Michael Jhon ]
Course: [fundamentals of programming course work]

Data model
----------
MENU_ITEMS : dict
    {
        "Item Name": {"category": "Meals", "price": 12000},
        ...
    }

RIDERS : list
    ["Rider name", ...]  -- the fixed pool of riders the canteen can
    assign completed orders to.

ORDERS : dict
    {
        1: {
            "items": {"Item Name": qty, ...},
            "subtotal": 24000,
            "delivery_fee": 3000,
            "total": 27000,
            "status": "Pending",       # Pending -> Out for Delivery -> Delivered
            "rider": None,             # rider name once assigned
            "placed_at": "2026-09-09 12:00:00",
        },
        ...
    }

Orders are persisted to a JSON log file so records survive between
programme runs.
"""

import json
import os
from datetime import datetime

# ---------------------------------------------------------------------------
# File paths used for persistence
# ---------------------------------------------------------------------------
ORDERS_FILE = "orders_log.json"

# Defined stages an order must pass through, in order. An order can only
# move to the very next stage in this list -- it can never skip ahead.
STATUS_STAGES = ["Pending", "Out for Delivery", "Delivered"]


# ---------------------------------------------------------------------------
# a) Menu setup
# ---------------------------------------------------------------------------
def initialise_menu():
    """
    Build the default restaurant menu: at least 8 items across at
    least 3 categories, each with a price.

    Returns:
        dict: the MENU_ITEMS data structure described at the top of
        this file.
    """
    menu = {
        "Chicken & Rice":  {"category": "Meals", "price": 15000},
        "Beef Stew & Posho": {"category": "Meals", "price": 12000},
        "Vegetable Pilau": {"category": "Meals", "price": 10000},
        "Rolex":           {"category": "Snacks", "price": 4000},
        "Chapati":         {"category": "Snacks", "price": 1500},
        "Samosa":          {"category": "Snacks", "price": 1000},
        "Soda (500ml)":    {"category": "Drinks", "price": 2500},
        "Bottled Water":   {"category": "Drinks", "price": 2000},
        "Fresh Juice":     {"category": "Drinks", "price": 5000},
    }
    return menu


def print_menu(menu):
    """Print the menu grouped by category."""
    print("\n===== CANTEEN MENU =====")
    categories = sorted(set(item["category"] for item in menu.values()))
    for category in categories:
        print(f"\n{category}:")
        for name, details in menu.items():
            if details["category"] == category:
                print(f"  {name:<20} {details['price']:>8,.0f}")
    print("=" * 26)


# ---------------------------------------------------------------------------
# b) Order taking
# ---------------------------------------------------------------------------
def calculate_delivery_fee(subtotal):
    """
    Work out the delivery fee based on the order's total value, using
    tiered conditional logic (a stand-in for a distance-band fee model).

    Returns:
        float: the delivery fee to add to the subtotal.
    """
    if subtotal >= 50000:
        return 0            # Free delivery on large orders
    elif subtotal >= 20000:
        return 3000
    elif subtotal > 0:
        return 5000
    return 0


def build_order(menu, orders, next_order_id, items_and_quantities):
    """
    Create a new order from a dict of {item_name: quantity}, calculate
    its subtotal, delivery fee and total, and store it in ORDERS with
    status "Pending".

    Args:
        menu (dict): MENU_ITEMS
        orders (dict): ORDERS, modified in place
        next_order_id (int): the id to assign to this new order
        items_and_quantities (dict): {item_name: quantity}

    Returns:
        tuple(bool, str): (success flag, message explaining the outcome)
    """
    if not items_and_quantities:
        return False, "An order must contain at least one item."

    subtotal = 0
    for item_name, quantity in items_and_quantities.items():
        if item_name not in menu:
            return False, f"'{item_name}' is not on the menu."
        if quantity <= 0:
            return False, f"Quantity for '{item_name}' must be greater than zero."
        subtotal += menu[item_name]["price"] * quantity

    delivery_fee = calculate_delivery_fee(subtotal)
    total = subtotal + delivery_fee

    orders[next_order_id] = {
        "items": items_and_quantities,
        "subtotal": subtotal,
        "delivery_fee": delivery_fee,
        "total": total,
        "status": STATUS_STAGES[0],
        "rider": None,
        "placed_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    }
    return True, (
        f"Order #{next_order_id} placed. Subtotal: {subtotal:,.0f}, "
        f"Delivery fee: {delivery_fee:,.0f}, Total: {total:,.0f}"
    )


# ---------------------------------------------------------------------------
# c) Rider assignment and status tracking
# ---------------------------------------------------------------------------
def get_busy_riders(orders):
    """Return the set of rider names currently out on a delivery."""
    return {
        order["rider"]
        for order in orders.values()
        if order["rider"] is not None and order["status"] == "Out for Delivery"
    }


def get_available_riders(riders, orders):
    """Return the list of riders not currently out on a delivery."""
    busy = get_busy_riders(orders)
    return [rider for rider in riders if rider not in busy]


def assign_rider(orders, riders, order_id, rider_name):
    """
    Assign an available rider to an order and move that order to the
    "Out for Delivery" stage. Only works on orders still "Pending".

    Returns:
        tuple(bool, str): (success flag, message explaining the outcome)
    """
    if order_id not in orders:
        return False, f"Order #{order_id} does not exist."

    order = orders[order_id]
    if order["status"] != "Pending":
        return False, (
            f"Order #{order_id} is '{order['status']}' and cannot be assigned "
            f"a rider from this state."
        )

    if rider_name not in riders:
        return False, f"'{rider_name}' is not a recognised rider."

    if rider_name not in get_available_riders(riders, orders):
        return False, f"Rider '{rider_name}' is already out on a delivery."

    order["rider"] = rider_name
    order["status"] = "Out for Delivery"
    return True, f"Order #{order_id} assigned to {rider_name} and marked 'Out for Delivery'."


def advance_order_status(orders, order_id):
    """
    Move an order to the next stage in STATUS_STAGES. Refuses to skip
    stages (e.g. Pending straight to Delivered) and refuses to move
    past the final stage.

    Returns:
        tuple(bool, str): (success flag, message explaining the outcome)
    """
    if order_id not in orders:
        return False, f"Order #{order_id} does not exist."

    order = orders[order_id]
    current_index = STATUS_STAGES.index(order["status"])

    if current_index == len(STATUS_STAGES) - 1:
        return False, f"Order #{order_id} is already '{order['status']}' (final stage)."

    if order["status"] == "Pending":
        return False, (
            f"Order #{order_id} must be assigned a rider (moving it to "
            f"'Out for Delivery') before it can progress further."
        )

    next_status = STATUS_STAGES[current_index + 1]
    order["status"] = next_status
    return True, f"Order #{order_id} is now '{next_status}'."


# ---------------------------------------------------------------------------
# d) Sales and reporting
# ---------------------------------------------------------------------------
def compute_daily_stats(orders):
    """
    Compute the day's total revenue (from Delivered orders), the
    best-selling item by quantity across all orders, and the number of
    orders in each status category.

    Returns:
        dict: {
            "total_revenue": float,
            "best_seller": str or None,
            "status_counts": {status: count, ...},
        }
    """
    total_revenue = sum(
        order["total"] for order in orders.values() if order["status"] == "Delivered"
    )

    item_totals = {}
    for order in orders.values():
        for item_name, quantity in order["items"].items():
            item_totals[item_name] = item_totals.get(item_name, 0) + quantity
    best_seller = max(item_totals, key=item_totals.get) if item_totals else None

    status_counts = {stage: 0 for stage in STATUS_STAGES}
    for order in orders.values():
        status_counts[order["status"]] += 1

    return {
        "total_revenue": total_revenue,
        "best_seller": best_seller,
        "status_counts": status_counts,
    }


def print_daily_stats(orders):
    stats = compute_daily_stats(orders)
    print("\n===== DAILY SALES REPORT =====")
    print(f"Total revenue (Delivered orders): {stats['total_revenue']:,.0f}")
    print(f"Best-selling item: {stats['best_seller'] or 'No orders yet'}")
    print("Orders by status:")
    for status, count in stats["status_counts"].items():
        print(f"  {status:<18}: {count}")
    print("=" * 30)


# ---------------------------------------------------------------------------
# e) File persistence
# ---------------------------------------------------------------------------
def save_data(orders):
    """Save all orders to the JSON log file."""
    try:
        with open(ORDERS_FILE, "w") as f:
            json.dump(orders, f, indent=2)
        return True, "Order log saved successfully."
    except OSError as error:
        return False, f"Could not save order log: {error}"


def load_data():
    """
    Load orders from the JSON log file. Falls back to an empty order
    log if the file is missing or corrupted, instead of crashing.

    Returns:
        tuple(dict, int, str): (orders, next_order_id, status_message)
    """
    if os.path.exists(ORDERS_FILE):
        try:
            with open(ORDERS_FILE, "r") as f:
                raw = json.load(f)
            # JSON object keys are always strings; convert back to int ids
            orders = {int(k): v for k, v in raw.items()}
            next_id = max(orders.keys(), default=0) + 1
            return orders, next_id, "Order log loaded from file."
        except (json.JSONDecodeError, OSError, ValueError):
            return {}, 1, "Order log file was missing/corrupted — starting with an empty log."
    return {}, 1, "No saved order log found — starting fresh."


# ---------------------------------------------------------------------------
# Input validation helpers
# ---------------------------------------------------------------------------
def prompt_nonempty(prompt_text):
    """Keep asking until the user provides a non-blank string."""
    while True:
        value = input(prompt_text).strip()
        if value:
            return value
        print("This field cannot be empty. Please try again.")


def prompt_positive_int(prompt_text):
    """Keep asking until the user provides a valid positive integer."""
    while True:
        raw = input(prompt_text).strip()
        if raw.isdigit() and int(raw) > 0:
            return int(raw)
        print("Please enter a whole number greater than zero.")


def prompt_choice(prompt_text, valid_options):
    """Keep asking until the user picks one of a fixed set of options."""
    while True:
        value = input(prompt_text).strip()
        if value in valid_options:
            return value
        print(f"Invalid option. Choose from: {', '.join(valid_options)}")


# ---------------------------------------------------------------------------
# f) Menu-driven driver programme
# ---------------------------------------------------------------------------
def run_take_order_menu(menu, orders, next_order_id_holder):
    print("\n--- Take New Order ---")
    print_menu(menu)
    items_and_quantities = {}
    while True:
        item_name = prompt_choice(
            "Item name (exactly as listed, blank to finish): ", list(menu.keys()) + [""]
        )
        if item_name == "":
            break
        quantity = prompt_positive_int(f"Quantity of '{item_name}': ")
        items_and_quantities[item_name] = items_and_quantities.get(item_name, 0) + quantity

    order_id = next_order_id_holder[0]
    success, message = build_order(menu, orders, order_id, items_and_quantities)
    print(message)
    if success:
        next_order_id_holder[0] += 1


def run_assign_rider_menu(orders, riders):
    print("\n--- Assign Rider to Order ---")
    available = get_available_riders(riders, orders)
    print(f"Available riders: {', '.join(available) if available else 'none right now'}")
    order_id = prompt_positive_int("Order number: ")
    rider_name = prompt_nonempty("Rider name: ")
    success, message = assign_rider(orders, riders, order_id, rider_name)
    print(message)


def run_advance_status_menu(orders):
    print("\n--- Advance Order Status ---")
    order_id = prompt_positive_int("Order number: ")
    success, message = advance_order_status(orders, order_id)
    print(message)


def print_order_list(orders):
    print("\n===== ALL ORDERS =====")
    if not orders:
        print("No orders placed yet.")
    for order_id, order in sorted(orders.items()):
        items_str = ", ".join(f"{name} x{qty}" for name, qty in order["items"].items())
        rider = order["rider"] or "unassigned"
        print(
            f"#{order_id} [{order['status']}] {items_str} | "
            f"Total: {order['total']:,.0f} | Rider: {rider} | {order['placed_at']}"
        )
    print("=" * 24)


def display_main_menu():
    print("\n=========================================")
    print(" CAMPUS FOOD DELIVERY & ORDER MANAGEMENT")
    print("=========================================")
    print("1. View menu")
    print("2. Take a new order")
    print("3. Assign a rider to an order")
    print("4. Advance an order's status")
    print("5. View all orders")
    print("6. Daily sales report")
    print("7. Save order log now")
    print("8. Exit")


def main():
    menu = initialise_menu()
    riders = ["Brian", "Grace", "Moses", "Patience"]

    print("Loading saved order log...")
    orders, next_order_id, status_message = load_data()
    next_order_id_holder = [next_order_id]
    print(status_message)

    while True:
        display_main_menu()
        choice = prompt_choice("Choose an option (1-8): ", [str(i) for i in range(1, 9)])

        if choice == "1":
            print_menu(menu)
        elif choice == "2":
            run_take_order_menu(menu, orders, next_order_id_holder)
        elif choice == "3":
            run_assign_rider_menu(orders, riders)
        elif choice == "4":
            run_advance_status_menu(orders)
        elif choice == "5":
            print_order_list(orders)
        elif choice == "6":
            print_daily_stats(orders)
        elif choice == "7":
            success, message = save_data(orders)
            print(message)
        elif choice == "8":
            success, message = save_data(orders)
            print(message)
            print("Goodbye!")
            break


if __name__ == "__main__":
    main()