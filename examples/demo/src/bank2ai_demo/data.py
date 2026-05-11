"""Hardcoded test data for bank2ai demo server.

This module provides realistic banking test data that can be used
to demonstrate the bank2ai specification without requiring a real bank.
"""

from datetime import date, timedelta

# Test accounts
ACCOUNTS = [
    {
        "id": "acc_checking_001",
        "name": "Main Checking",
        "accountNumber": "1234-56-789012",
        "bban": "1234-56-789012",
        "bic": "DEMOUS33XXX",
        "currency": "USD",
        "balance": 5420.50,
        "availableBalance": 5420.50,
        "overdraftLimit": 0.0,
        # Typed balances exercise the optional `balances` array; the
        # top-level `balance` / `availableBalance` scalars stay as
        # derived shortcuts that clients on the lean payload path can
        # use without parsing the array.
        "balances": [
            {
                "type": "ClosingBooked",
                "amount": 5420.50,
                "currency": "USD",
                "asOf": "2024-03-15T08:30:00Z",
            },
            {
                "type": "InterimAvailable",
                "amount": 5420.50,
                "currency": "USD",
                "asOf": "2024-03-15T08:30:00Z",
            },
        ],
        "ownerName": "Alex Demo",
        "product": "Demo Everyday Checking",
        "status": "Enabled",
        "usage": "Private",
        "accountType": "Current",
        "isWithdrawalAccount": True,
        "isDefaultAccount": True,
        "openedDate": "2018-04-12",
        "balanceUpdatedAt": "2024-03-15T08:30:00Z",
    },
    {
        "id": "acc_savings_001",
        "name": "Emergency Fund",
        "accountNumber": "1234-56-789013",
        "bban": "1234-56-789013",
        "bic": "DEMOUS33XXX",
        "currency": "USD",
        "balance": 15000.00,
        "availableBalance": 15000.00,
        "overdraftLimit": 0.0,
        "ownerName": "Alex Demo",
        "product": "Demo High-Yield Savings",
        "status": "Enabled",
        "usage": "Private",
        "accountType": "Savings",
        "isWithdrawalAccount": True,
        "isDefaultAccount": False,
        "openedDate": "2020-09-03",
        "balanceUpdatedAt": "2024-03-15T08:30:00Z",
    },
    {
        "id": "acc_credit_001",
        "name": "Visa Credit Card",
        "accountNumber": "1234-56-789014",
        "maskedPan": "411111xxxxxx4242",
        "bic": "DEMOUS33XXX",
        "currency": "USD",
        "balance": -850.25,
        "availableBalance": 4149.75,
        "overdraftLimit": 5000.0,
        "ownerName": "Alex Demo",
        "product": "Demo Visa Signature",
        "status": "Enabled",
        "usage": "Private",
        "accountType": "Credit",
        "isWithdrawalAccount": False,
        "isDefaultAccount": False,
        "openedDate": "2021-06-18",
        "balanceUpdatedAt": "2024-03-15T08:30:00Z",
        "statementBalance": 1240.75,
        "minimumPaymentDue": 35.00,
        "paymentDueDate": "2024-04-05",
        "statementClosingDate": "2024-04-12",
    },
]

# Generate transactions for the last 90 days
def generate_transactions():
    """Generate realistic transaction history."""
    transactions = []
    today = date.today()

    # Recurring monthly transactions. The salary entry is richly populated
    # to exercise the optional ISO 20022 fields (counterparty, transactionCode,
    # remittanceInformation, endToEndId).
    transactions.append({
        "id": "tx_001",
        "accountId": "acc_checking_001",
        "description": "Monthly Salary",
        "counterpartyName": "Acme Corp",
        "amount": 4500.00,
        "bookingDate": (today - timedelta(days=5)).isoformat(),
        "categoryId": "Income",
        "counterparty": {
            "name": "Acme Corp",
            "accountIdentifier": {
                "type": "accountNumber",
                "accountNumber": "9999-99-999999",
                "country": "US",
            },
        },
        "transactionCode": {
            "domain": "PMNT",
            "family": "RCDT",
            "subFamily": "SALA",
        },
        "remittanceInformation": {
            "unstructured": "Payroll, March 2024",
        },
        "endToEndId": "ACME-PAY-2024-03-15",
    })

    transactions.append({
        "id": "tx_002",
        "accountId": "acc_checking_001",
        "description": "Rent Payment",
        "amount": -1200.00,
        "bookingDate": (today - timedelta(days=3)).isoformat(),
        "categoryId": "Housing",
    })

    # Groceries
    grocery_stores = ["Whole Foods", "Trader Joe's", "Safeway", "Local Market"]
    for i, days_ago in enumerate([2, 7, 14, 21, 28, 35]):
        transactions.append({
            "id": f"tx_grocery_{i:03d}",
            "accountId": "acc_checking_001",
            "description": grocery_stores[i % len(grocery_stores)],
            "amount": -85.50 - (i * 5),
            "bookingDate": (today - timedelta(days=days_ago)).isoformat(),
            "categoryId": "Groceries",
        })

    # Transportation
    transactions.extend([
        {
            "id": "tx_gas_001",
            "accountId": "acc_checking_001",
            "description": "Shell Gas Station",
            "amount": -45.00,
            "bookingDate": (today - timedelta(days=4)).isoformat(),
            "categoryId": "Transport",
        },
        {
            "id": "tx_transit_001",
            "accountId": "acc_checking_001",
            "description": "Monthly Metro Pass",
            "amount": -120.00,
            "bookingDate": (today - timedelta(days=1)).isoformat(),
            "categoryId": "Transport",
        },
    ])

    # Entertainment (charged to credit card)
    transactions.extend([
        {
            "id": "tx_netflix_001",
            "accountId": "acc_credit_001",
            "description": "Netflix Subscription",
            "amount": -15.99,
            "bookingDate": (today - timedelta(days=10)).isoformat(),
            "categoryId": "DiningAndEntertainment",
        },
        {
            "id": "tx_movie_001",
            "accountId": "acc_credit_001",
            "description": "Cinema Tickets",
            "amount": -32.00,
            "bookingDate": (today - timedelta(days=12)).isoformat(),
            "categoryId": "DiningAndEntertainment",
        },
        {
            "id": "tx_spotify_001",
            "accountId": "acc_credit_001",
            "description": "Spotify Premium",
            "amount": -9.99,
            "bookingDate": (today - timedelta(days=8)).isoformat(),
            "categoryId": "DiningAndEntertainment",
        },
    ])

    # Utilities
    transactions.extend([
        {
            "id": "tx_electric_001",
            "accountId": "acc_checking_001",
            "description": "Electric Company",
            "amount": -85.00,
            "bookingDate": (today - timedelta(days=15)).isoformat(),
            "categoryId": "Utilities",
        },
        {
            "id": "tx_internet_001",
            "accountId": "acc_checking_001",
            "description": "Internet Service Provider",
            "amount": -60.00,
            "bookingDate": (today - timedelta(days=18)).isoformat(),
            "categoryId": "Utilities",
        },
    ])

    # Dining (charged to credit card)
    restaurants = ["Pizza Place", "Sushi Bar", "Burger Joint", "Thai Restaurant", "Coffee Shop"]
    for i, days_ago in enumerate([1, 6, 9, 13, 20, 25, 30]):
        transactions.append({
            "id": f"tx_dining_{i:03d}",
            "accountId": "acc_credit_001",
            "description": restaurants[i % len(restaurants)],
            "amount": -25.00 - (i * 3),
            "bookingDate": (today - timedelta(days=days_ago)).isoformat(),
            "categoryId": "DiningAndEntertainment",
        })

    # Healthcare
    transactions.append({
        "id": "tx_pharmacy_001",
        "accountId": "acc_checking_001",
        "description": "Pharmacy Co-pay",
        "amount": -20.00,
        "bookingDate": (today - timedelta(days=22)).isoformat(),
        "categoryId": "Health",
    })

    # Shopping (charged to credit card)
    transactions.extend([
        {
            "id": "tx_amazon_001",
            "accountId": "acc_credit_001",
            "description": "Amazon.com",
            "amount": -78.50,
            "bookingDate": (today - timedelta(days=11)).isoformat(),
            "categoryId": "Shopping",
        },
        {
            "id": "tx_clothing_001",
            "accountId": "acc_credit_001",
            "description": "Clothing Store",
            "amount": -125.00,
            "bookingDate": (today - timedelta(days=16)).isoformat(),
            "categoryId": "Shopping",
        },
    ])

    # Foreign-currency transactions: amount is in the user's default currency
    # (USD here); originalCurrency / originalAmount carry the original.
    transactions.extend([
        {
            "id": "tx_paris_dining_001",
            "accountId": "acc_credit_001",
            "description": "Le Petit Bistro, Paris",
            "amount": -54.20,
            "originalCurrency": "EUR",
            "originalAmount": -49.80,
            "bookingDate": (today - timedelta(days=17)).isoformat(),
            "categoryId": "DiningAndEntertainment",
        },
        {
            "id": "tx_london_shopping_001",
            "accountId": "acc_credit_001",
            "description": "Selfridges, London",
            "amount": -210.45,
            "originalCurrency": "GBP",
            "originalAmount": -165.00,
            "bookingDate": (today - timedelta(days=24)).isoformat(),
            "categoryId": "Shopping",
        },
    ])

    # Sort by date (newest first)
    transactions.sort(key=lambda x: x["bookingDate"], reverse=True)

    return transactions

TRANSACTIONS = generate_transactions()

# Categories. Demo uses canonical bank2ai category ids
# (`bank2ai.CANONICAL_CATEGORY_IDS`) so client-side taxonomies built
# against the demo work unchanged against any conformant server.
CATEGORIES = [
    {"id": "Income", "name": "Income"},
    {"id": "Housing", "name": "Housing"},
    {"id": "Groceries", "name": "Groceries"},
    {"id": "Transport", "name": "Transport"},
    {"id": "DiningAndEntertainment", "name": "Dining & Entertainment"},
    {"id": "Utilities", "name": "Utilities"},
    {"id": "Health", "name": "Health"},
    {"id": "Shopping", "name": "Shopping"},
]

# Recipients. Demo carries one Icelandic-style recipient (BBAN + kennitala)
# so the Icelandic transfer flow runs end-to-end against the spec, plus US
# (accountNumber + routing) and UK (IBAN) flavours to exercise every variant
# of the AccountIdentifier discriminated union.
RECIPIENTS = [
    {
        "id": "rcpt_001",
        "name": "Jón Jónsson",
        "accountIdentifier": {
            "type": "bban",
            "bban": "0133-26-007890",
            "country": "IS",
        },
        "nationalId": {
            "value": "010190-1234",
            "country": "IS",
            "type": "kennitala",
        },
        "isFavorite": True,
        "nickname": "Friend",
    },
    {
        "id": "rcpt_002",
        "name": "John Doe",
        "accountIdentifier": {
            "type": "accountNumber",
            "accountNumber": "5678-90-123457",
            "country": "US",
            "routing": "021000021",
        },
        "nationalId": {
            "value": "234-56-7890",
            "country": "US",
            "type": "ssn",
        },
        "isFavorite": False,
        "nickname": "Contractor",
    },
    {
        "id": "rcpt_003",
        "name": "Alice Johnson",
        "accountIdentifier": {
            "type": "iban",
            "iban": "GB29NWBK60161331926819",
        },
        "isFavorite": True,
        "nickname": "Family",
    },
    {
        "id": "rcpt_004",
        "name": "Bob Williams",
        "accountIdentifier": {
            "type": "accountNumber",
            "accountNumber": "5678-90-123459",
            "country": "US",
        },
        "isFavorite": False,
        "nickname": "Landlord",
    },
]
