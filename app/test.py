from web3 import Web3
from web3.middleware import ExtraDataToPOAMiddleware

from app.settings.settings import settings

MY_WALLET_ADDRESS = settings.POLYMARKET_WALLET_ADDR
MY_PRIVATE_KEY = settings.POLYMARKET_WALLET_PRIVATE_KEY
POLYGON_RPC_URL = "https://polygon-rpc.com"
MARKET_QUESTION_ID = "0x6edc6c77c16ef3ba1bcd646159f12f8b8a39528e500dcff95b9220ccfbb75141"  # varies by market
print("Attempting to connect to the Polygon network...")
w3 = Web3(Web3.HTTPProvider(POLYGON_RPC_URL))
w3.middleware_onion.inject(ExtraDataToPOAMiddleware, layer=0)
if not w3.is_connected():
    print("❌ Error: Could not connect to the Polygon network. Please check your POLYGON_RPC_URL.")
    exit()
print(f"✅ Successfully connected to the Polygon network.")
POLYMARKET_CONTRACT_ADDRESS = "0x4D97DCd97eC945f40cF65F87097ACe5EA0476045"  # stays the same
POLYMARKET_ABI = """
[
  {
    "inputs": [
      { "internalType": "address", "name": "collateral", "type": "address" },
      { "internalType": "bytes32", "name": "parentCollectionId", "type": "bytes32" },
      { "internalType": "bytes32", "name": "conditionId", "type": "bytes32" },
      { "internalType": "uint256[]", "name": "indexSets", "type": "uint256[]" }
    ],
    "name": "redeemPositions",
    "outputs": [],
    "stateMutability": "nonpayable",
    "type": "function"
  }
]
"""
polymarket_contract = w3.eth.contract(address=POLYMARKET_CONTRACT_ADDRESS, abi=POLYMARKET_ABI)
USDC_ADDRESS = "0x2791Bca1f2de4661ED88A30C99A7a9449Aa84174"   #
PARENT_COLLECTION_ID = b'\0' * 32

# This represents which outcomes you are redeeming.
# To redeem a full set of shares (e.g., if you hold both "Yes" and "No"), use.[1, 2]
# This is the standard way to redeem the underlying $1.00 of collateral.
# If you only hold the winning "Yes" shares, you can try.[1]
# If you only hold the winning "No" shares, you can try.[2]
INDEX_SETS_TO_REDEEM = [1, 2]  # Recommended: [1, 2] for a full redemption.

print(f"\n🔧 Preparing to redeem shares for market: {MARKET_QUESTION_ID}")

try:
    print("Building transaction...")
    transaction = polymarket_contract.functions.redeemPositions(
        USDC_ADDRESS,
        PARENT_COLLECTION_ID,
        w3.to_bytes(hexstr=MARKET_QUESTION_ID),
        INDEX_SETS_TO_REDEEM
    ).build_transaction({
        'from': MY_WALLET_ADDRESS,
        'nonce': w3.eth.get_transaction_count(MY_WALLET_ADDRESS),
        'gasPrice': w3.eth.gas_price,
        'gas': 250000
    })
    print("✅ Transaction built.")
    print("Signing transaction...")
    signed_txn = w3.eth.account.sign_transaction(transaction, private_key=MY_PRIVATE_KEY)
    print("✅ Transaction signed.")
    print(f"Raw signed transaction: {signed_txn}")
    print("Sending transaction to the network...")
    txn_hash = w3.eth.send_raw_transaction(signed_txn.raw_transaction)
    print(f"🚀 Transaction sent! View on Polygonscan: https://polygonscan.com/tx/{txn_hash.hex()}")
    print(f"Raw transaction hash {txn_hash}")
    print("Waiting for confirmation...")
    txn_receipt = w3.eth.wait_for_transaction_receipt(txn_hash, timeout=300)
    if txn_receipt['status'] == 1:
        print("\n🎉 Success! Your shares have been redeemed for USDC.")
        print(f"Raw txn_receipt: {txn_receipt}")
    else:
        print("\n❌ Transaction failed. Check the transaction on Polygonscan for details.")

except Exception as e:
    print(f"\nMencho")
