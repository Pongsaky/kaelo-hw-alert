import asyncio
import pytest
import logging
from unittest.mock import patch, AsyncMock
from datetime import datetime


class TestEnhancedHardwareController:
    """Test suite for enhanced HardwareController class with PWM support"""

    @pytest.fixture
    def hardware_controller(self):
        """Create HardwareController in simulation mode"""
        with patch("hardware_controller.GPIOD_AVAILABLE", False):
            from hardware_controller import HardwareController

            controller = HardwareController()
            yield controller
            controller.cleanup()

    def test_initialization_simulation_mode(self, hardware_controller):
        """Test controller initialization in simulation mode"""
        assert hardware_controller.red_pin == 17
        assert hardware_controller.green_pin == 27
        assert hardware_controller.blue_pin == 22
        assert hardware_controller.buzzer_pin == 24
        assert hardware_controller.pwm_freq == 500
        assert not hardware_controller.common_anode
        assert not hardware_controller.is_active
        assert hardware_controller.gpio is None
        assert hardware_controller.pwm_r is None
        assert hardware_controller.pwm_g is None
        assert hardware_controller.pwm_b is None

    def test_custom_pin_initialization(self):
        """Test initialization with custom pin numbers and PWM settings"""
        with patch("hardware_controller.GPIOD_AVAILABLE", False):
            from hardware_controller import HardwareController

            controller = HardwareController(
                red_pin=5,
                green_pin=6,
                blue_pin=13,
                buzzer_pin=19,
                pwm_freq=1000,
                common_anode=True,
            )

            assert controller.red_pin == 5
            assert controller.green_pin == 6
            assert controller.blue_pin == 13
            assert controller.buzzer_pin == 19
            assert controller.pwm_freq == 1000
            assert controller.common_anode
            controller.cleanup()

    def test_pwm_color_setting_simulation(self, hardware_controller):
        """Test PWM RGB color setting in simulation mode (should not crash)"""
        # Test with float values (0.0 to 1.0)
        hardware_controller.set_rgb_color(1.0, 0.0, 0.5)  # Magenta
        hardware_controller.set_rgb_color(0.3, 0.7, 0.2)  # Custom green
        hardware_controller.set_rgb_color(0.8, 0.4, 0.0)  # Orange

    def test_rgb_off_simulation(self, hardware_controller):
        """Test RGB off in simulation mode"""
        hardware_controller.rgb_off()

    def test_clamp01_function(self):
        """Test the clamp01 utility function"""
        from hardware_controller import clamp01

        assert clamp01(0.5) == 0.5
        assert clamp01(-0.1) == 0.0
        assert clamp01(1.5) == 1.0
        assert clamp01(0) == 0.0
        assert clamp01(1) == 1.0

    def test_beep_function_simulation(self, hardware_controller):
        """Test beep function in simulation mode"""
        # Should complete without error
        hardware_controller.beep(duration=0.1, pause=0.1, times=2)

    @pytest.mark.asyncio
    async def test_async_beep_function(self, hardware_controller):
        """Test async beep function"""
        # Should complete without error
        await hardware_controller.async_beep(duration=0.05, pause=0.05, times=3)

    @pytest.mark.asyncio
    async def test_queue_alert(self, hardware_controller):
        """Test alert queueing functionality"""
        alert_id = await hardware_controller.queue_alert(
            severity="high", alert_type="temperature", device_id="sensor_01"
        )

        assert alert_id is not None
        assert len(alert_id) == 8
        assert hardware_controller.alert_queue.qsize() == 1

    @pytest.mark.asyncio
    async def test_all_severity_levels(self, hardware_controller):
        """Test all alert severity levels"""
        severities = ["critical", "high", "medium", "low"]

        for severity in severities:
            alert_id = await hardware_controller.queue_alert(
                severity=severity, alert_type="test", device_id="test_device"
            )
            assert alert_id is not None
            assert len(alert_id) == 8

        assert hardware_controller.alert_queue.qsize() == 4

    @pytest.mark.asyncio
    async def test_enhanced_critical_alert_execution(self, hardware_controller):
        """Test enhanced critical alert with pulsing effect"""
        alert_data = {
            "alert_id": "test_critical",
            "severity": "critical",
            "alert_type": "fire",
            "device_id": "smoke_detector_01",
            "timestamp": datetime.now().isoformat(),
        }

        with patch("asyncio.sleep", new_callable=AsyncMock):
            with patch("asyncio.get_event_loop") as mock_loop:
                # Mock rapid completion
                mock_loop.return_value.time.side_effect = [0, 0.1, 10.1]

                await hardware_controller._execute_alert(alert_data)

        assert not hardware_controller.is_active

    @pytest.mark.asyncio
    async def test_enhanced_high_alert_execution(self, hardware_controller):
        """Test enhanced high alert with breathing effect"""
        alert_data = {
            "alert_id": "test_high",
            "severity": "high",
            "alert_type": "temperature",
            "device_id": "temp_sensor_01",
            "timestamp": datetime.now().isoformat(),
        }

        with patch("asyncio.sleep", new_callable=AsyncMock):
            with patch("asyncio.get_event_loop") as mock_loop:
                mock_loop.return_value.time.side_effect = [0, 0.1, 5.1]

                await hardware_controller._execute_alert(alert_data)

        assert not hardware_controller.is_active

    @pytest.mark.asyncio
    async def test_enhanced_medium_alert_execution(self, hardware_controller):
        """Test enhanced medium alert with fade effect"""
        alert_data = {
            "alert_id": "test_medium",
            "severity": "medium",
            "alert_type": "humidity",
            "device_id": "humidity_sensor_01",
            "timestamp": datetime.now().isoformat(),
        }

        with patch("asyncio.sleep", new_callable=AsyncMock):
            with patch("asyncio.get_event_loop") as mock_loop:
                mock_loop.return_value.time.side_effect = [0, 0.1, 5.1]

                await hardware_controller._execute_alert(alert_data)

        assert not hardware_controller.is_active

    @pytest.mark.asyncio
    async def test_enhanced_low_alert_execution(self, hardware_controller):
        """Test enhanced low alert with gentle glow"""
        with patch("asyncio.sleep", new_callable=AsyncMock) as mock_sleep:
            await hardware_controller._low_alert()
            mock_sleep.assert_called_with(2.0)

    @pytest.mark.asyncio
    async def test_invalid_severity_handling(self, hardware_controller):
        """Test handling of invalid severity levels"""
        alert_data = {
            "alert_id": "test_invalid",
            "severity": "invalid_level",
            "alert_type": "test",
            "device_id": "test_device",
            "timestamp": datetime.now().isoformat(),
        }

        # Should handle gracefully without raising
        await hardware_controller._execute_alert(alert_data)
        assert not hardware_controller.is_active

    @pytest.mark.asyncio
    async def test_queue_processor_startup(self, hardware_controller):
        """Test alert queue processor startup"""
        # Should start without error
        await hardware_controller.start_queue_processor()

    def test_cleanup_simulation_mode(self, hardware_controller):
        """Test cleanup in simulation mode"""
        # Should complete without error
        hardware_controller.cleanup()

    @pytest.mark.asyncio
    async def test_concurrent_alert_queueing(self, hardware_controller):
        """Test concurrent alert queueing"""
        tasks = [
            hardware_controller.queue_alert("high", "temp", "sensor1"),
            hardware_controller.queue_alert("critical", "fire", "sensor2"),
            hardware_controller.queue_alert("low", "battery", "sensor3"),
        ]

        alert_ids = await asyncio.gather(*tasks)

        assert len(alert_ids) == 3
        assert hardware_controller.alert_queue.qsize() == 3
        assert all(len(aid) == 8 for aid in alert_ids)


class TestGPIOWrapper:
    """Test GPIO wrapper class in simulation mode"""

    def test_gpio_initialization_simulation(self):
        """Test GPIO wrapper initialization"""
        with patch("hardware_controller.GPIOD_AVAILABLE", False):
            # Should not create GPIO object in simulation mode
            pass

    def test_soft_pwm_initialization_simulation(self):
        """Test SoftPWM initialization"""
        with patch("hardware_controller.GPIOD_AVAILABLE", False):
            # Should not create SoftPWM objects in simulation mode
            pass


@pytest.mark.asyncio
async def test_integration_enhanced_workflow():
    """Integration test for enhanced workflow with PWM effects"""
    with patch("hardware_controller.GPIOD_AVAILABLE", False):
        from hardware_controller import HardwareController

        controller = HardwareController(
            pwm_freq=1000,
            common_anode=False,  # Custom configuration
        )

        # Start queue processor
        await controller.start_queue_processor()

        # Test enhanced RGB controls with PWM values
        controller.set_rgb_color(0.8, 0.0, 0.0)  # Bright red
        controller.set_rgb_color(0.0, 0.6, 0.0)  # Medium green
        controller.set_rgb_color(0.0, 0.0, 0.4)  # Dim blue
        controller.rgb_off()

        # Queue multiple alerts
        alert_ids = []
        for severity in ["low", "medium", "high", "critical"]:
            alert_id = await controller.queue_alert(
                severity=severity,
                alert_type="integration_test",
                device_id=f"device_{severity}",
            )
            alert_ids.append(alert_id)

        assert len(alert_ids) == 4
        assert controller.alert_queue.qsize() == 4

        # Test enhanced beep functions
        controller.beep(0.1, 0.1, 2)
        await controller.async_beep(0.05, 0.05, 3)

        # Process some alerts manually
        for _ in range(2):
            if not controller.alert_queue.empty():
                alert_data = await controller.alert_queue.get()
                await controller._execute_alert(alert_data)

        controller.cleanup()


@pytest.mark.asyncio
async def test_pwm_timing_patterns():
    """Test PWM-based alert timing patterns"""
    with patch("hardware_controller.GPIOD_AVAILABLE", False):
        from hardware_controller import HardwareController

        controller = HardwareController()

        # Test critical alert with pulsing (should complete quickly with mocked time)
        import time

        start_time = time.time()

        with patch("asyncio.sleep", new_callable=AsyncMock):
            with patch("asyncio.get_event_loop") as mock_loop:
                # Mock time progression for critical alert (10 second duration)
                mock_loop.return_value.time.side_effect = [0, 5.0, 10.1]
                await controller._critical_alert()

        elapsed = time.time() - start_time
        assert elapsed < 1.0  # Should complete quickly with mocked timing

        # Test breathing effect timing for high alert
        with patch("asyncio.sleep", new_callable=AsyncMock):
            with patch("asyncio.get_event_loop") as mock_loop:
                mock_loop.return_value.time.side_effect = [0, 2.5, 5.1]
                await controller._high_alert()

        controller.cleanup()


def test_pwm_color_gradients():
    """Test various PWM color gradients"""
    with patch("hardware_controller.GPIOD_AVAILABLE", False):
        from hardware_controller import HardwareController

        controller = HardwareController()

        # Test smooth color gradients (0.0 to 1.0 range)
        gradient_colors = [
            (0.0, 0.0, 0.0),  # Off
            (0.1, 0.0, 0.0),  # Dim red
            (0.5, 0.0, 0.0),  # Medium red
            (1.0, 0.0, 0.0),  # Bright red
            (1.0, 0.3, 0.0),  # Orange
            (1.0, 1.0, 0.0),  # Yellow
            (0.0, 1.0, 0.0),  # Green
            (0.0, 1.0, 1.0),  # Cyan
            (0.0, 0.0, 1.0),  # Blue
            (1.0, 0.0, 1.0),  # Magenta
            (1.0, 1.0, 1.0),  # White
        ]

        for r, g, b in gradient_colors:
            controller.set_rgb_color(r, g, b)

        controller.rgb_off()
        controller.cleanup()


def test_logging_enhanced_behavior(caplog):
    """Test logging output for enhanced controller"""
    with patch("hardware_controller.GPIOD_AVAILABLE", False):
        from hardware_controller import HardwareController

        with caplog.at_level(logging.INFO):
            controller = HardwareController(pwm_freq=1000, common_anode=True)

        # Check that simulation mode message was logged
        assert "Running in simulation mode" in caplog.text
        controller.cleanup()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
