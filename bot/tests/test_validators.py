import pytest
from bot.validators import (
    validate_symbol,
    validate_side,
    validate_order_type,
    validate_quantity,
    validate_price,
    validate_stop_price,
)


class TestValidateSymbol:
    """Test suite for validate_symbol function"""

    def test_valid_symbol_uppercase(self):
        """Test valid symbol in uppercase"""
        result = validate_symbol("BTCUSDT")
        assert result == "BTCUSDT"

    def test_valid_symbol_lowercase(self):
        """Test valid symbol in lowercase is normalized to uppercase"""
        result = validate_symbol("btcusdt")
        assert result == "BTCUSDT"

    def test_valid_symbol_mixed_case(self):
        """Test valid symbol in mixed case is normalized to uppercase"""
        result = validate_symbol("EthUsdt")
        assert result == "ETHUSDT"

    def test_valid_symbol_other_pairs(self):
        """Test various valid trading pairs"""
        assert validate_symbol("ETHUSDT") == "ETHUSDT"
        assert validate_symbol("BNBUSDT") == "BNBUSDT"
        assert validate_symbol("SOLUSDT") == "SOLUSDT"

    def test_symbol_missing_usdt_suffix(self):
        """Test that symbol without USDT suffix raises ValueError"""
        with pytest.raises(ValueError, match="must end with USDT"):
            validate_symbol("BTC")

    def test_symbol_wrong_suffix(self):
        """Test that symbol with wrong suffix raises ValueError"""
        with pytest.raises(ValueError, match="must end with USDT"):
            validate_symbol("BTCETH")

    def test_symbol_empty_string(self):
        """Test that empty string raises ValueError"""
        with pytest.raises(ValueError, match="non-empty"):
            validate_symbol("")

    def test_symbol_none(self):
        """Test that None raises ValueError"""
        with pytest.raises((ValueError, AttributeError)):
            validate_symbol(None)

    def test_symbol_only_usdt(self):
        """Test that just 'USDT' raises ValueError"""
        with pytest.raises(ValueError):
            validate_symbol("USDT")

    def test_symbol_with_spaces(self):
        """Test that symbol with spaces is rejected"""
        with pytest.raises(ValueError):
            validate_symbol("BTC USDT")


class TestValidateSide:
    """Test suite for validate_side function"""

    def test_valid_side_buy_uppercase(self):
        """Test valid BUY side"""
        result = validate_side("BUY")
        assert result == "BUY"

    def test_valid_side_sell_uppercase(self):
        """Test valid SELL side"""
        result = validate_side("SELL")
        assert result == "SELL"

    def test_valid_side_buy_lowercase(self):
        """Test BUY in lowercase is normalized to uppercase"""
        result = validate_side("buy")
        assert result == "BUY"

    def test_valid_side_sell_lowercase(self):
        """Test SELL in lowercase is normalized to uppercase"""
        result = validate_side("sell")
        assert result == "SELL"

    def test_valid_side_mixed_case(self):
        """Test mixed case sides are normalized"""
        assert validate_side("Buy") == "BUY"
        assert validate_side("Sell") == "SELL"

    def test_invalid_side_long(self):
        """Test that LONG is rejected"""
        with pytest.raises(ValueError, match="BUY or SELL"):
            validate_side("LONG")

    def test_invalid_side_short(self):
        """Test that SHORT is rejected"""
        with pytest.raises(ValueError, match="BUY or SELL"):
            validate_side("SHORT")

    def test_invalid_side_empty(self):
        """Test that empty string is rejected"""
        with pytest.raises(ValueError):
            validate_side("")

    def test_invalid_side_none(self):
        """Test that None is rejected"""
        with pytest.raises((ValueError, AttributeError)):
            validate_side(None)

    def test_invalid_side_typo(self):
        """Test that typos are rejected"""
        with pytest.raises(ValueError):
            validate_side("BUUY")


class TestValidateOrderType:
    """Test suite for validate_order_type function"""

    def test_valid_market_uppercase(self):
        """Test valid MARKET order type"""
        result = validate_order_type("MARKET")
        assert result == "MARKET"

    def test_valid_limit_uppercase(self):
        """Test valid LIMIT order type"""
        result = validate_order_type("LIMIT")
        assert result == "LIMIT"

    def test_valid_stop_market_uppercase(self):
        """Test valid STOP_MARKET order type"""
        result = validate_order_type("STOP_MARKET")
        assert result == "STOP_MARKET"

    def test_valid_order_type_lowercase(self):
        """Test order types in lowercase are normalized"""
        assert validate_order_type("market") == "MARKET"
        assert validate_order_type("limit") == "LIMIT"
        assert validate_order_type("stop_market") == "STOP_MARKET"

    def test_invalid_order_type_oco(self):
        """Test that OCO is rejected"""
        with pytest.raises(ValueError, match="MARKET, LIMIT, or STOP_MARKET"):
            validate_order_type("OCO")

    def test_invalid_order_type_twap(self):
        """Test that TWAP is rejected"""
        with pytest.raises(ValueError):
            validate_order_type("TWAP")

    def test_invalid_order_type_grid(self):
        """Test that GRID is rejected"""
        with pytest.raises(ValueError):
            validate_order_type("GRID")

    def test_invalid_order_type_empty(self):
        """Test that empty string is rejected"""
        with pytest.raises(ValueError):
            validate_order_type("")

    def test_invalid_order_type_none(self):
        """Test that None is rejected"""
        with pytest.raises((ValueError, AttributeError)):
            validate_order_type(None)


class TestValidateQuantity:
    """Test suite for validate_quantity function"""

    def test_valid_quantity(self):
        """Test valid quantity"""
        symbol_info = {
            "stepSize": 0.00001,
            "minOrderQty": 0.0001,
            "maxOrderQty": 10000,
        }
        result = validate_quantity(0.001, symbol_info)
        assert result == 0.001

    def test_quantity_respects_step_size(self):
        """Test that quantity is rounded to stepSize"""
        symbol_info = {
            "stepSize": 0.01,  # Only 2 decimals allowed
            "minOrderQty": 0.01,
            "maxOrderQty": 10000,
        }
        result = validate_quantity(0.015, symbol_info)
        assert result == 0.01  # Rounded down to nearest stepSize

    def test_quantity_below_minimum(self):
        """Test that quantity below minOrderQty raises ValueError"""
        symbol_info = {
            "stepSize": 0.00001,
            "minOrderQty": 0.0001,
            "maxOrderQty": 10000,
        }
        with pytest.raises(ValueError, match="minimum"):
            validate_quantity(0.00001, symbol_info)

    def test_quantity_above_maximum(self):
        """Test that quantity above maxOrderQty raises ValueError"""
        symbol_info = {
            "stepSize": 0.00001,
            "minOrderQty": 0.0001,
            "maxOrderQty": 10,
        }
        with pytest.raises(ValueError, match="maximum"):
            validate_quantity(100, symbol_info)

    def test_quantity_negative(self):
        """Test that negative quantity raises ValueError"""
        symbol_info = {
            "stepSize": 0.00001,
            "minOrderQty": 0.0001,
            "maxOrderQty": 10000,
        }
        with pytest.raises(ValueError, match="positive"):
            validate_quantity(-0.001, symbol_info)

    def test_quantity_zero(self):
        """Test that zero quantity raises ValueError"""
        symbol_info = {
            "stepSize": 0.00001,
            "minOrderQty": 0.0001,
            "maxOrderQty": 10000,
        }
        with pytest.raises(ValueError, match="positive"):
            validate_quantity(0, symbol_info)

    def test_quantity_none(self):
        """Test that None quantity raises error"""
        symbol_info = {
            "stepSize": 0.00001,
            "minOrderQty": 0.0001,
            "maxOrderQty": 10000,
        }
        with pytest.raises((ValueError, TypeError)):
            validate_quantity(None, symbol_info)


class TestValidatePrice:
    """Test suite for validate_price function"""

    def test_valid_price_for_limit_order(self):
        """Test valid price for LIMIT order"""
        symbol_info = {
            "tickSize": 0.01,
            "minPrice": 0.01,
            "maxPrice": 1000000,
        }
        result = validate_price(67850.50, "LIMIT", symbol_info)
        assert result == 67850.50

    def test_valid_price_for_stop_market_order(self):
        """Test valid price for STOP_MARKET order"""
        symbol_info = {
            "tickSize": 0.01,
            "minPrice": 0.01,
            "maxPrice": 1000000,
        }
        result = validate_price(65000.00, "STOP_MARKET", symbol_info)
        assert result == 65000.00

    def test_price_none_for_market_order(self):
        """Test that price=None is allowed for MARKET orders"""
        result = validate_price(None, "MARKET", {})
        assert result is None

    def test_price_required_for_limit_order(self):
        """Test that price is required for LIMIT orders"""
        symbol_info = {
            "tickSize": 0.01,
            "minPrice": 0.01,
            "maxPrice": 1000000,
        }
        with pytest.raises(ValueError, match="required for LIMIT"):
            validate_price(None, "LIMIT", symbol_info)

    def test_price_required_for_stop_market_order(self):
        """Test that price is required for STOP_MARKET orders"""
        symbol_info = {
            "tickSize": 0.01,
            "minPrice": 0.01,
            "maxPrice": 1000000,
        }
        with pytest.raises(ValueError, match="required"):
            validate_price(None, "STOP_MARKET", symbol_info)

    def test_price_respects_tick_size(self):
        """Test that price is rounded to tickSize"""
        symbol_info = {
            "tickSize": 0.1,  # Only 1 decimal allowed
            "minPrice": 0.01,
            "maxPrice": 1000000,
        }
        result = validate_price(67850.567, "LIMIT", symbol_info)
        assert result == 67850.5  # Rounded to nearest tickSize

    def test_price_below_minimum(self):
        """Test that price below minPrice raises ValueError"""
        symbol_info = {
            "tickSize": 0.01,
            "minPrice": 0.01,
            "maxPrice": 1000000,
        }
        with pytest.raises(ValueError, match="minimum"):
            validate_price(0.001, "LIMIT", symbol_info)

    def test_price_above_maximum(self):
        """Test that price above maxPrice raises ValueError"""
        symbol_info = {
            "tickSize": 0.01,
            "minPrice": 0.01,
            "maxPrice": 100,
        }
        with pytest.raises(ValueError, match="maximum"):
            validate_price(1000, "LIMIT", symbol_info)

    def test_price_negative(self):
        """Test that negative price raises ValueError"""
        symbol_info = {
            "tickSize": 0.01,
            "minPrice": 0.01,
            "maxPrice": 1000000,
        }
        with pytest.raises(ValueError, match="positive"):
            validate_price(-100, "LIMIT", symbol_info)


class TestValidateStopPrice:
    """Test suite for validate_stop_price function"""

    def test_valid_stop_price_for_stop_market(self):
        """Test valid stop price for STOP_MARKET order"""
        result = validate_stop_price(65000.00, "STOP_MARKET")
        assert result == 65000.00

    def test_stop_price_none_for_market_order(self):
        """Test that stop_price=None is allowed for MARKET orders"""
        result = validate_stop_price(None, "MARKET")
        assert result is None

    def test_stop_price_none_for_limit_order(self):
        """Test that stop_price=None is allowed for LIMIT orders"""
        result = validate_stop_price(None, "LIMIT")
        assert result is None

    def test_stop_price_required_for_stop_market(self):
        """Test that stop_price is required for STOP_MARKET orders"""
        with pytest.raises(ValueError, match="required for STOP_MARKET"):
            validate_stop_price(None, "STOP_MARKET")

    def test_stop_price_negative(self):
        """Test that negative stop price raises ValueError"""
        with pytest.raises(ValueError, match="positive"):
            validate_stop_price(-1000, "STOP_MARKET")

    def test_stop_price_zero(self):
        """Test that zero stop price raises ValueError"""
        with pytest.raises(ValueError, match="positive"):
            validate_stop_price(0, "STOP_MARKET")

    def test_stop_price_positive_large(self):
        """Test that large positive stop price is valid"""
        result = validate_stop_price(1000000, "STOP_MARKET")
        assert result == 1000000
