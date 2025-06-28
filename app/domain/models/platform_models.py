import ast
from datetime import datetime
from typing import Annotated, Optional, List

from pydantic import BaseModel, BeforeValidator


class MetaData(BaseModel):
    created_at: datetime

StrList = Annotated[List[str], BeforeValidator(lambda v: ast.literal_eval(v) if isinstance(v, str) else v)]

class PolymarketMarket(BaseModel):
    # tags
    id: Optional[str] = None
    # descriptive fields
    acceptingOrders: Optional[bool] = None
    active: Optional[bool] = None
    bestBid: Optional[float] = None
    bestAsk: Optional[float] = None
    clobTokenIds: Optional[StrList] = None # List encoded as a string
    closed: Optional[bool] = None
    competitive: Optional[float] = None
    conditionId: Optional[str] = None
    description: Optional[str] = None
    enableOrderBook: Optional[bool] = None
    endDate: Optional[datetime] = None
    # events: Optional[str]= None # List of events (any)
    fee: Optional[float] = None
    groupItemTitle: Optional[str] = None
    lastTradePrice: Optional[float] = None # returns an int
    liquidityClob: Optional[float] = None
    negRisk: Optional[bool] = None
    negRiskMarketID: Optional[str] = None
    oneDayPriceChange: Optional[float] = None
    oneHourPriceChange: Optional[float] = None
    oneWeekPriceChange: Optional[float] = None
    oneMonthPriceChange: Optional[float] = None
    orderMinSize: Optional[float] = None # returns an int
    outcomes: Optional[StrList] = None # returns a list of strs
    outcomePrices: Optional[StrList] = None # returns a list of strs
    question: Optional[str] = None
    questionID: Optional[str] = None
    resolutionSource: Optional[str] = None
    ready: Optional[bool] = None
    restricted: Optional[bool] = None
    slug: Optional[str] = None
    startDate: Optional[datetime] = None
    spread: Optional[float] = None
    sportsMarketType: Optional[str] = None
    updatedAt: Optional[datetime] = None
    volume24hrClob: Optional[float] = None
    volume1wkClob: Optional[float] = None
    volume1moClob: Optional[float] = None
    volume1yrClob: Optional[float] = None

    class Config:
        extra = 'ignore'

class KalshiMarket(BaseModel):
    # tags
    ticker : Optional[str] = None
    event_ticker : Optional[str] = None
    # descriptive fields
    market_type : Optional[str] = None
    title : Optional[str] = None
    subtitle : Optional[str] = None
    yes_sub_title : Optional[str] = None
    no_sub_title : Optional[str] = None
    open_time : Optional[datetime] = None # comes in as a datetime in format ISO8601
    close_time : Optional[datetime] = None # comes in as a datetime in format ISO8601
    expected_expiration_time : Optional[datetime] = None # comes in as a datetime in format ISO8601
    expiration_time: Optional[datetime] = None
    latest_expiration_time: Optional[datetime] = None
    settlement_timer_seconds: Optional[int] = None
    status: Optional[str] = None
    response_price_units : Optional[str] = None
    tick_size : Optional[int] = None
    yes_bid : Optional[int] = None
    yes_ask : Optional[int] = None
    no_bid : Optional[int] = None
    no_ask : Optional[int] = None
    last_price : Optional[int] = None
    previous_yes_bid : Optional[int] = None
    previous_yes_ask : Optional[int]  = None
    previous_price : Optional[int] = None
    volume : Optional[int] = None
    volume_24h : Optional[int] = None
    liquidity : Optional[int] = None
    open_interest : Optional[int] =None
    result : Optional[str] = None
    can_close_early: Optional[bool] = None
    expiration_value : Optional[str] = None
    category : Optional[str]  = None
    risk_limit_cents : Optional[int] = None
    rules_primary : Optional[str]  = None
    rules_secondary : Optional[str] = None
    strike_type : Optional[str]= None
    floor_strike : Optional[float] = None
    cap_strike : Optional[float] = None

    class Config:
        extra = 'ignore'