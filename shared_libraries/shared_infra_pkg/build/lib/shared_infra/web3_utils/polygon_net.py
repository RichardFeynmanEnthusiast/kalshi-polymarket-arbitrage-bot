from web3 import Web3
from eth_account import Account
from eth_typing import HexStr, ChecksumAddress

RPC_URL = 'https://polygon-rpc.com/'  # Polygon's Remote Procedure Calls url (e.g. query data or submit txn)
USDC_e_CONTRACT_ADDR = '0x2791Bca1f2de4661ED88A30C99A7a9449Aa84174'
USDC_CONTRACT_ADDR = '0x3c499c542cEF5E3811e1192ce70d8cC03d5c3359'
web3 = Web3(Web3.HTTPProvider(RPC_URL))

# -- helpers
def valid_eth_private_key(private_key_hex: str) -> bool:
    """
    Checks if a given string represents a valid Ethereum private key format.

    Args:
        private_key_hex: The private key string (hexadecimal, with or without '0x' prefix).

    Returns:
        True if the format is valid, False otherwise.
    """
    try:
        # This will raise an exception if the key format is invalid.
        Account.from_key(private_key_hex)
        return HexStr(private_key_hex)
    except Exception as e:
        raise ValueError(f"Wrong key format: {e}")

def valid_eth_wallet_addr(address: str) -> ChecksumAddress:
    try:
        if not Web3.is_address(address):
            raise ValueError(f"{address} is not a valid Ethereum wallet address.")
        return Web3.to_checksum_address
    except Exception as e:
        raise e

# -- balance related utils

def get_matic_balance(public_key : ChecksumAddress, block_number : int = 12):
    # on polygon network the native currency used for gas is MATIC
    raw_balance = web3.eth.get_balance(public_key, web3.eth.block_number-block_number)
    readable_balance = raw_balance / 10 ** 18
    return readable_balance

def get_usdc_e_balance(public_key : ChecksumAddress, block_number : int = 12):

    # Minimal ERC-20 ABI for balanceOf and decimals
    erc20_abi = [
        {
            "constant": True,
            "inputs": [{"name": "_owner", "type": "address"}],
            "name": "balanceOf",
            "outputs": [{"name": "balance", "type": "uint256"}],
            "type": "function"
        },
        {
            "constant": True,
            "inputs": [],
            "name": "decimals",
            "outputs": [{"name": "", "type": "uint8"}],
            "type": "function"
        }
    ]

    # Create contract instance
    usdc_contract = web3.eth.contract(address=USDC_e_CONTRACT_ADDR, abi=erc20_abi)

    # Call balanceOf
    raw_balance = usdc_contract.functions.balanceOf(public_key).call(block_identifier=web3.eth.block_number - block_number)
    decimals = usdc_contract.functions.decimals().call()

    # Convert to human-readable format
    readable_balance = raw_balance / (10 ** decimals)
    return readable_balance