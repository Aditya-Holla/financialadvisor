"""Models for myStockDNA integration output."""

from typing import Optional, List
from pydantic import BaseModel, Field


class StockDNAAnalysis(BaseModel):
    """Structured output from myStockDNA model analysis."""
    
    symbol: str = Field(..., description="Stock ticker symbol")
    risk_score: float = Field(..., ge=0.0, le=1.0, description="Risk score between 0 and 1")
    growth_potential: float = Field(..., ge=0.0, le=1.0, description="Growth potential score between 0 and 1")
    value_score: float = Field(..., ge=0.0, le=1.0, description="Value score between 0 and 1")
    momentum_score: float = Field(..., ge=0.0, le=1.0, description="Momentum score between 0 and 1")
    sector: Optional[str] = Field(None, description="Sector classification")
    market_cap: Optional[str] = Field(None, description="Market capitalization category")
    recommendation: str = Field(..., description="Recommendation: BUY, SELL, or HOLD")
    confidence: float = Field(..., ge=0.0, le=1.0, description="Confidence level between 0 and 1")
    reasoning: str = Field(..., description="Brief reasoning for the recommendation")


class StockDNABatchResponse(BaseModel):
    """Batch response from myStockDNA for multiple symbols."""
    
    analyses: List[StockDNAAnalysis] = Field(..., description="List of stock analyses")
    timestamp: str = Field(..., description="ISO timestamp of the analysis")

