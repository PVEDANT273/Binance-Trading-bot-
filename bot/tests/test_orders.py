import pytest
from unittest.mock import Mock, MagicMock, patch, call
from bot.orders import OrderManager
from bot.client import BinanceAPIError, NetworkError


class TestOrderManager:
    """Test suite for OrderManager class"""

    @pytest.fixture
    def mock_client(self):
        """Create a mocked BinanceClient"""
        client = Mock()
        client.get_exchange_info = Mock(
            return_value={
                "symbol": "BTCUSDT",
                "stepSize": 0.00001,
                "tickSize": 0.01,
                "minOrderQty": 0.0001,
                "maxOrderQty": 10000,
                "minPrice": 0.01,
                "maxPrice": 1000000,
            }
        )
        return client

    @pytest.fixture
    def manager(self, mock_client):
        """Create OrderManager with mocked client"""
        return OrderManager(mock_client)

    # ===== SUCCESSFUL MARKET ORDERS =====

    def test_place_market_buy_order_success(self, manager, mock_client):
        """Test successful MARKET BUY order placement"""
        mock_client.post.return_value = {
            "orderId": 123456789,
            "symbol": "BTCUSDT",
            "status": "FILLED",
            "side": "BUY",
            "type": "MARKET",
            "executedQty": 0.001,
            "cummulativeQuoteQty": 67.85,
            "avgPrice": 67850.00,
        }

        response = manager.place_order(
            symbol="BTCUSDT",
            side="BUY",
            order_type="MARKET",
            quantity=0.001,
        )

        assert response["orderId"] == 123456789
        assert response["status"] == "FILLED"
        assert response["executedQty"] == 0.001
        assert response["avgPrice"] == 67850.00

        # Verify client was called with correct endpoint
        mock_client.post.assert_called_once()
        call_args = mock_client.post.call_args
        assert "/fapi/v1/order" in call_args[0][0]

    def test_place_market_sell_order_success(self, manager, mock_client):
        """Test successful MARKET SELL order placement"""
        mock_client.post.return_value = {
            "orderId": 987654321,
            "symbol": "ETHUSDT",
            "status": "FILLED",
            "side": "SELL",
            "type": "MARKET",
            "executedQty": 0.5,
            "avgPrice": 3200.00,
        }

        response = manager.place_order(
            symbol="ETHUSDT",
            side="SELL",
            order_type="MARKET",
            quantity=0.5,
        )

        assert response["orderId"] == 987654321
        assert response["side"] == "SELL"
        assert response["executedQty"] == 0.5

    # ===== SUCCESSFUL LIMIT ORDERS =====

    def test_place_limit_order_success(self, manager, mock_client):
        """Test successful LIMIT order placement"""
        mock_client.post.return_value = {
            "orderId": 111111111,
            "symbol": "BTCUSDT",
            "status": "NEW",  # LIMIT orders start as NEW (not executed yet)
            "side": "BUY",
            "type": "LIMIT",
            "price": 60000.00,
            "executedQty": 0,
            "origQty": 0.001,
        }

        response = manager.place_order(
            symbol="BTCUSDT",
            side="BUY",
            order_type="LIMIT",
            quantity=0.001,
            price=60000.00,
        )

        assert response["orderId"] == 111111111
        assert response["status"] == "NEW"
        assert response["type"] == "LIMIT"

        # Verify price was included in the POST request
        call_args = mock_client.post.call_args
        assert call_args[0][1]["price"] == 60000.00

    def test_place_limit_order_without_price_fails(self, manager, mock_client):
        """Test that LIMIT order without price is rejected"""
        with pytest.raises(ValueError, match="required for LIMIT"):
            manager.place_order(
                symbol="BTCUSDT",
                side="BUY",
                order_type="LIMIT",
                quantity=0.001,
                price=None,  # Missing price!
            )

        # Verify no API call was made
        mock_client.post.assert_not_called()

    # ===== SUCCESSFUL STOP_MARKET ORDERS =====

    def test_place_stop_market_order_success(self, manager, mock_client):
        """Test successful STOP_MARKET order placement"""
        mock_client.post.return_value = {
            "orderId": 222222222,
            "symbol": "BTCUSDT",
            "status": "NEW",
            "side": "SELL",
            "type": "STOP_MARKET",
            "stopPrice": 65000.00,
            "origQty": 0.001,
            "executedQty": 0,
        }

        response = manager.place_order(
            symbol="BTCUSDT",
            side="SELL",
            order_type="STOP_MARKET",
            quantity=0.001,
            stop_price=65000.00,
        )

        assert response["orderId"] == 222222222
        assert response["type"] == "STOP_MARKET"
        assert response["stopPrice"] == 65000.00

        # Verify stop_price was included
        call_args = mock_client.post.call_args
        assert call_args[0][1]["stopPrice"] == 65000.00

    def test_place_stop_market_order_without_stop_price_fails(
        self, manager, mock_client
    ):
        """Test that STOP_MARKET order without stop_price is rejected"""
        with pytest.raises(ValueError, match="required for STOP_MARKET"):
            manager.place_order(
                symbol="BTCUSDT",
                side="SELL",
                order_type="STOP_MARKET",
                quantity=0.001,
                stop_price=None,  # Missing stop price!
            )

        # Verify no API call was made
        mock_client.post.assert_not_called()

    # ===== VALIDATION ERRORS =====

    def test_invalid_symbol_rejected(self, manager, mock_client):
        """Test that invalid symbol is rejected before API call"""
        with pytest.raises(ValueError):
            manager.place_order(
                symbol="INVALID",  # Doesn't end in USDT
                side="BUY",
                order_type="MARKET",
                quantity=0.001,
            )

        # Verify no API call was made
        mock_client.post.assert_not_called()

    def test_invalid_side_rejected(self, manager, mock_client):
        """Test that invalid side is rejected before API call"""
        with pytest.raises(ValueError):
            manager.place_order(
                symbol="BTCUSDT",
                side="LONG",  # Invalid side
                order_type="MARKET",
                quantity=0.001,
            )

        mock_client.post.assert_not_called()

    def test_invalid_order_type_rejected(self, manager, mock_client):
        """Test that invalid order type is rejected before API call"""
        with pytest.raises(ValueError):
            manager.place_order(
                symbol="BTCUSDT",
                side="BUY",
                order_type="OCO",  # Invalid type
                quantity=0.001,
            )

        mock_client.post.assert_not_called()

    def test_quantity_below_minimum_rejected(self, manager, mock_client):
        """Test that quantity below minimum is rejected before API call"""
        with pytest.raises(ValueError, match="minimum"):
            manager.place_order(
                symbol="BTCUSDT",
                side="BUY",
                order_type="MARKET",
                quantity=0.00001,  # Below minOrderQty (0.0001)
            )

        mock_client.post.assert_not_called()

    def test_negative_quantity_rejected(self, manager, mock_client):
        """Test that negative quantity is rejected"""
        with pytest.raises(ValueError, match="positive"):
            manager.place_order(
                symbol="BTCUSDT",
                side="BUY",
                order_type="MARKET",
                quantity=-0.001,
            )

        mock_client.post.assert_not_called()

    def test_price_below_minimum_rejected(self, manager, mock_client):
        """Test that price below minimum is rejected before API call"""
        with pytest.raises(ValueError, match="minimum"):
            manager.place_order(
                symbol="BTCUSDT",
                side="BUY",
                order_type="LIMIT",
                quantity=0.001,
                price=0.001,  # Below minPrice (0.01)
            )

        mock_client.post.assert_not_called()

    # ===== BINANCE API ERRORS =====

    def test_binance_api_error_insufficient_margin(self, manager, mock_client):
        """Test handling of Binance API error: insufficient margin"""
        mock_client.post.side_effect = BinanceAPIError(
            code=-2019, message="Margin is insufficient"
        )

        with pytest.raises(BinanceAPIError):
            manager.place_order(
                symbol="BTCUSDT",
                side="BUY",
                order_type="MARKET",
                quantity=0.001,
            )

    def test_binance_api_error_invalid_symbol(self, manager, mock_client):
        """Test handling of Binance API error: invalid symbol"""
        # Reset mock for this test
        mock_client.get_exchange_info.side_effect = BinanceAPIError(
            code=-1013, message="Invalid symbol"
        )

        with pytest.raises(BinanceAPIError):
            manager.place_order(
                symbol="BTCUSDT",
                side="BUY",
                order_type="MARKET",
                quantity=0.001,
            )

    def test_binance_api_error_order_would_trigger_immediately(
        self, manager, mock_client
    ):
        """Test handling of Binance API error: order would trigger immediately"""
        mock_client.post.side_effect = BinanceAPIError(
            code=-2010, message="Order would trigger immediately"
        )

        with pytest.raises(BinanceAPIError):
            manager.place_order(
                symbol="BTCUSDT",
                side="SELL",
                order_type="STOP_MARKET",
                quantity=0.001,
                stop_price=100000,  # Stop price higher than current price
            )

    # ===== NETWORK ERRORS =====

    def test_network_timeout_during_order_placement(self, manager, mock_client):
        """Test handling of network timeout"""
        mock_client.post.side_effect = NetworkError("Connection timeout")

        with pytest.raises(NetworkError):
            manager.place_order(
                symbol="BTCUSDT",
                side="BUY",
                order_type="MARKET",
                quantity=0.001,
            )

    def test_network_error_during_exchange_info_fetch(self, manager, mock_client):
        """Test handling of network error when fetching exchange info"""
        mock_client.get_exchange_info.side_effect = NetworkError(
            "Failed to connect"
        )

        with pytest.raises(NetworkError):
            manager.place_order(
                symbol="BTCUSDT",
                side="BUY",
                order_type="MARKET",
                quantity=0.001,
            )

    def test_connection_refused(self, manager, mock_client):
        """Test handling of connection refused"""
        mock_client.post.side_effect = NetworkError("Connection refused")

        with pytest.raises(NetworkError):
            manager.place_order(
                symbol="BTCUSDT",
                side="BUY",
                order_type="MARKET",
                quantity=0.001,
            )

    # ===== RESPONSE PARSING =====

    def test_format_response_extracts_correct_fields(self, manager, mock_client):
        """Test that format_response extracts only the required fields"""
        raw_response = {
            "orderId": 123456789,
            "clientOrderId": "web_abc123",
            "symbol": "BTCUSDT",
            "status": "FILLED",
            "side": "BUY",
            "type": "MARKET",
            "executedQty": 0.001,
            "cummulativeQuoteQty": 67.85,
            "avgPrice": 67850.00,
            "origQty": 0.001,
            "timeInForce": "GTC",
            "createTime": 1234567890,
            "updateTime": 1234567891,
            "isWorking": True,
            "origQuoteOrderQty": 67.85,
        }

        mock_client.post.return_value = raw_response

        response = manager.place_order(
            symbol="BTCUSDT",
            side="BUY",
            order_type="MARKET",
            quantity=0.001,
        )

        # Only these fields should be in the formatted response
        assert "orderId" in response
        assert "status" in response
        assert "executedQty" in response
        assert "avgPrice" in response

        # These fields should NOT be in the formatted response
        assert "clientOrderId" not in response
        assert "createTime" not in response
        assert "updateTime" not in response

    # ===== EDGE CASES =====

    def test_very_small_valid_quantity(self, manager, mock_client):
        """Test placing order with very small but valid quantity"""
        mock_client.post.return_value = {
            "orderId": 333333333,
            "status": "FILLED",
            "executedQty": 0.0001,
            "avgPrice": 67850.00,
        }

        response = manager.place_order(
            symbol="BTCUSDT",
            side="BUY",
            order_type="MARKET",
            quantity=0.0001,  # Minimum valid
        )

        assert response["executedQty"] == 0.0001

    def test_large_valid_quantity(self, manager, mock_client):
        """Test placing order with large but valid quantity"""
        mock_client.post.return_value = {
            "orderId": 444444444,
            "status": "FILLED",
            "executedQty": 1000.0,
            "avgPrice": 67850.00,
        }

        response = manager.place_order(
            symbol="BTCUSDT",
            side="BUY",
            order_type="MARKET",
            quantity=1000.0,  # Large but within maxOrderQty
        )

        assert response["executedQty"] == 1000.0

    def test_symbol_case_insensitive(self, manager, mock_client):
        """Test that symbol validation is case-insensitive"""
        mock_client.post.return_value = {
            "orderId": 555555555,
            "status": "FILLED",
            "executedQty": 0.001,
            "avgPrice": 67850.00,
        }

        # Should accept lowercase and normalize it
        response = manager.place_order(
            symbol="btcusdt",
            side="BUY",
            order_type="MARKET",
            quantity=0.001,
        )

        assert response["orderId"] == 555555555

    def test_order_with_all_optional_parameters(self, manager, mock_client):
        """Test order placement with all parameters specified"""
        mock_client.post.return_value = {
            "orderId": 666666666,
            "status": "NEW",
            "executedQty": 0,
            "origQty": 0.001,
        }

        response = manager.place_order(
            symbol="BTCUSDT",
            side="BUY",
            order_type="STOP_MARKET",
            quantity=0.001,
            price=None,  # Not needed for STOP_MARKET (but could be provided)
            stop_price=65000.00,  # Required for STOP_MARKET
        )

        assert response["orderId"] == 666666666

    # ===== LOGGING VERIFICATION =====

    def test_order_is_logged(self, manager, mock_client):
        """Test that order placement is logged"""
        mock_client.post.return_value = {
            "orderId": 777777777,
            "status": "FILLED",
            "executedQty": 0.001,
            "avgPrice": 67850.00,
        }

        # This test just verifies no exceptions occur during logging
        # In a real scenario, you'd mock the logger and check log calls
        response = manager.place_order(
            symbol="BTCUSDT",
            side="BUY",
            order_type="MARKET",
            quantity=0.001,
        )

        assert response["orderId"] == 777777777
