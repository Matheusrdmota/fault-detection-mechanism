def get_pods():
    return [
        "carts-db-594b68dc85-zdw6k",
        "carts-f4f6c98b9-r5wxx",
        "catalogue-6d8b8988d-z4k7s",
        "catalogue-db-5c796cfb68-cxk72",
        "front-end-55c969566c-58z8l",
        "orders-685d756fb5-9gtr9",
        "orders-db-67c8d5f459-k5gx4",
        "payment-56bcfc857f-5kcpp",
        "queue-master-5f4477db4c-z4pfh",
        "rabbitmq-97cbcbdbc-tn9hg",
        "session-db-67c8bfcb9c-7zxqd",
        "shipping-5c7bc7f48f-hmgfx",
        "user-6776ddd957-lcbsz"
    ]

def get_pods_label():
    return [
        "carts-db",
        "carts",
        "catalogue",
        "catalogue-db",
        "front-end",
        "orders",
        "orders-db",
        "payment",
        "queue-master",
        "rabbitmq",
        "session-db",
        "shipping",
        "user"
    ]