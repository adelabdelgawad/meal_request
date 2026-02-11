"""
Test HRIS On-Shift Filtering Logic

This test verifies the attendance filtering logic that determines
if an employee is still on shift based on in/out times.
"""

import pytest
from datetime import datetime, timedelta

from db.schemas import AttendanceRecord
from api.services.hris_service import HRISService
from core.config import settings


class TestOnShiftFiltering:
    """Test the _is_still_on_shift and _filter_on_shift_only methods."""

    def setup_method(self):
        """Initialize service for each test."""
        self.service = HRISService()
        # Use the configured minimum shift hours
        self.min_hours = settings.attendance.min_shift_hours

    def test_no_out_time_is_on_shift(self):
        """Employee with no out time should be on shift."""
        record = AttendanceRecord(
            employee_code=1001,
            time_in=datetime(2024, 12, 2, 10, 0, 0),
            time_out=None,
            working_hours=None,
        )
        assert self.service._is_still_on_shift(record) is True

    def test_out_time_less_than_min_hours_is_on_shift(self):
        """Employee with out < MIN_HOURS after in should be on shift."""
        base_time = datetime(2024, 12, 2, 10, 0, 0)

        # Test 2 minutes after in (way less than min_hours)
        record = AttendanceRecord(
            employee_code=1001,
            time_in=base_time,
            time_out=base_time + timedelta(minutes=2),
            working_hours=0.03,
        )
        assert self.service._is_still_on_shift(record) is True

        # Test 1.5 hours after in (still less than 2 hours default)
        record = AttendanceRecord(
            employee_code=1001,
            time_in=base_time,
            time_out=base_time + timedelta(hours=1, minutes=30),
            working_hours=1.5,
        )
        assert self.service._is_still_on_shift(record) is True

        # Test 1 hour 59 minutes after in (just under 2 hours)
        record = AttendanceRecord(
            employee_code=1001,
            time_in=base_time,
            time_out=base_time + timedelta(hours=1, minutes=59),
            working_hours=1.98,
        )
        assert self.service._is_still_on_shift(record) is True

    def test_out_time_equal_or_greater_min_hours_not_on_shift(self):
        """Employee with out >= MIN_HOURS after in should NOT be on shift."""
        base_time = datetime(2024, 12, 2, 10, 0, 0)

        # Test exactly 2 hours after in
        record = AttendanceRecord(
            employee_code=1001,
            time_in=base_time,
            time_out=base_time + timedelta(hours=2),
            working_hours=2.0,
        )
        assert self.service._is_still_on_shift(record) is False

        # Test 8 hours after in (full shift)
        record = AttendanceRecord(
            employee_code=1001,
            time_in=base_time,
            time_out=base_time + timedelta(hours=8),
            working_hours=8.0,
        )
        assert self.service._is_still_on_shift(record) is False

        # Test 12 hours after in
        record = AttendanceRecord(
            employee_code=1001,
            time_in=base_time,
            time_out=base_time + timedelta(hours=12),
            working_hours=12.0,
        )
        assert self.service._is_still_on_shift(record) is False

    def test_filter_on_shift_only_excludes_completed_shifts(self):
        """Filter should exclude records with valid out times."""
        base_time = datetime(2024, 12, 2, 10, 0, 0)

        records = [
            # Still on shift - no out
            AttendanceRecord(
                employee_code=1001,
                time_in=base_time,
                time_out=None,
                working_hours=None,
            ),
            # Still on shift - invalid out (10 mins)
            AttendanceRecord(
                employee_code=1002,
                time_in=base_time,
                time_out=base_time + timedelta(minutes=10),
                working_hours=0.17,
            ),
            # Completed shift - 8 hours (should be excluded)
            AttendanceRecord(
                employee_code=1003,
                time_in=base_time,
                time_out=base_time + timedelta(hours=8),
                working_hours=8.0,
            ),
            # Still on shift - 1 hour out
            AttendanceRecord(
                employee_code=1004,
                time_in=base_time,
                time_out=base_time + timedelta(hours=1),
                working_hours=1.0,
            ),
            # Completed shift - 2 hours exactly (should be excluded)
            AttendanceRecord(
                employee_code=1005,
                time_in=base_time,
                time_out=base_time + timedelta(hours=2),
                working_hours=2.0,
            ),
        ]

        filtered = self.service._filter_on_shift_only(records)

        # Should have 3 records (1001, 1002, 1004)
        assert len(filtered) == 3

        # Check employee codes
        employee_codes = [r.employee_code for r in filtered]
        assert 1001 in employee_codes
        assert 1002 in employee_codes
        assert 1004 in employee_codes
        assert 1003 not in employee_codes  # 8 hours - completed
        assert 1005 not in employee_codes  # 2 hours - completed

    def test_filter_clears_invalid_out_times(self):
        """Filter should clear time_out for invalid outs."""
        base_time = datetime(2024, 12, 2, 10, 0, 0)

        records = [
            AttendanceRecord(
                employee_code=1001,
                time_in=base_time,
                time_out=base_time + timedelta(minutes=30),  # Invalid out
                working_hours=0.5,
            ),
        ]

        filtered = self.service._filter_on_shift_only(records)

        assert len(filtered) == 1
        assert filtered[0].time_out is None
        assert filtered[0].working_hours is None

    def test_large_volume_filtering(self):
        """Test filtering with large volume of records."""
        base_time = datetime(2024, 12, 2, 8, 0, 0)

        # Create 1000 records with varying patterns
        records = []
        for i in range(1000):
            employee_code = 1000 + i

            if i % 5 == 0:
                # No out time (on shift)
                time_out = None
                working_hours = None
            elif i % 5 == 1:
                # Invalid out (30 mins - on shift)
                time_out = base_time + timedelta(minutes=30)
                working_hours = 0.5
            elif i % 5 == 2:
                # Invalid out (1.5 hours - on shift)
                time_out = base_time + timedelta(hours=1, minutes=30)
                working_hours = 1.5
            elif i % 5 == 3:
                # Valid out (8 hours - completed)
                time_out = base_time + timedelta(hours=8)
                working_hours = 8.0
            else:
                # Valid out (3 hours - completed)
                time_out = base_time + timedelta(hours=3)
                working_hours = 3.0

            records.append(AttendanceRecord(
                employee_code=employee_code,
                time_in=base_time,
                time_out=time_out,
                working_hours=working_hours,
            ))

        filtered = self.service._filter_on_shift_only(records)

        # i % 5 == 0, 1, 2 should be on shift (3 out of 5 = 60%)
        # 1000 * 0.6 = 600
        assert len(filtered) == 600

        # Verify all invalid outs are cleared
        for record in filtered:
            if record.employee_code % 5 in [1, 2]:
                # These originally had invalid outs
                assert record.time_out is None
                assert record.working_hours is None


class TestEdgeCases:
    """Test edge cases for the on-shift logic."""

    def setup_method(self):
        """Initialize service for each test."""
        self.service = HRISService()

    def test_midnight_crossover(self):
        """Test when in/out crosses midnight."""
        # In at 11 PM, out at 1 AM next day (2 hours = completed)
        record = AttendanceRecord(
            employee_code=1001,
            time_in=datetime(2024, 12, 2, 23, 0, 0),
            time_out=datetime(2024, 12, 3, 1, 0, 0),
            working_hours=2.0,
        )
        assert self.service._is_still_on_shift(record) is False

    def test_midnight_crossover_less_than_min(self):
        """Test when in/out crosses midnight but less than min hours."""
        # In at 11:30 PM, out at 12:30 AM next day (1 hour = on shift)
        record = AttendanceRecord(
            employee_code=1001,
            time_in=datetime(2024, 12, 2, 23, 30, 0),
            time_out=datetime(2024, 12, 3, 0, 30, 0),
            working_hours=1.0,
        )
        assert self.service._is_still_on_shift(record) is True

    def test_same_time_in_out(self):
        """Test when in and out are the same time (0 hours)."""
        record = AttendanceRecord(
            employee_code=1001,
            time_in=datetime(2024, 12, 2, 10, 0, 0),
            time_out=datetime(2024, 12, 2, 10, 0, 0),
            working_hours=0.0,
        )
        assert self.service._is_still_on_shift(record) is True

    def test_empty_records_list(self):
        """Test filtering empty list."""
        filtered = self.service._filter_on_shift_only([])
        assert filtered == []

    def test_all_completed_shifts(self):
        """Test when all records are completed shifts."""
        base_time = datetime(2024, 12, 2, 10, 0, 0)

        records = [
            AttendanceRecord(
                employee_code=1001,
                time_in=base_time,
                time_out=base_time + timedelta(hours=8),
                working_hours=8.0,
            ),
            AttendanceRecord(
                employee_code=1002,
                time_in=base_time,
                time_out=base_time + timedelta(hours=4),
                working_hours=4.0,
            ),
        ]

        filtered = self.service._filter_on_shift_only(records)
        assert len(filtered) == 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
