#!/usr/bin/env python3
# SPDX-FileCopyrightText: Copyright (c) 2016-2024, CloudZero, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0

import csv
import json
import os
import tempfile
import unittest.mock
from unittest.mock import patch, mock_open, MagicMock

import pytest
import requests

from anycost_example import (
    read_csv,
    process_usage_data,
    process_purchase_commitments,
    process_discounts,
    write_cbf_rows_to_csv,
    upload_to_anycost,
)


class TestReadCsv:
    def test_read_csv_success(self):
        csv_content = "name,value\ntest,123\nfoo,bar\n"
        with patch("builtins.open", mock_open(read_data=csv_content)):
            result = read_csv("test.csv")
            
        expected = [
            {"name": "test", "value": "123"},
            {"name": "foo", "value": "bar"}
        ]
        assert result == expected

    def test_read_csv_empty_file(self):
        csv_content = "name,value\n"
        with patch("builtins.open", mock_open(read_data=csv_content)):
            result = read_csv("empty.csv")
            
        assert result == []


class TestProcessUsageData:
    def test_process_usage_data_single_row(self):
        csv_data = [
            {
                "sku": "compute-engine",
                "instance_id": "12345",
                "usage_date": "2024-08-16T10:00:00Z",
                "cost": "100.00",
                "discount": "10.00"
            }
        ]
        
        with patch("anycost_example.read_csv", return_value=csv_data):
            result = process_usage_data("test.csv")
            
        expected = [{
            "lineitem/type": "Usage",
            "resource/service": "compute-engine",
            "resource/id": "instance-12345",
            "time/usage_start": "2024-08-16T10:00:00Z",
            "cost/cost": "100.00",
            "cost/discounted_cost": "90.00"
        }]
        assert result == expected

    def test_process_usage_data_negative_discount(self):
        csv_data = [
            {
                "sku": "storage",
                "instance_id": "67890",
                "usage_date": "2024-08-16T11:00:00Z",
                "cost": "50.00",
                "discount": "-5.00"
            }
        ]
        
        with patch("anycost_example.read_csv", return_value=csv_data):
            result = process_usage_data("test.csv")
            
        expected = [{
            "lineitem/type": "Usage",
            "resource/service": "storage",
            "resource/id": "instance-67890",
            "time/usage_start": "2024-08-16T11:00:00Z",
            "cost/cost": "50.00",
            "cost/discounted_cost": "45.00"
        }]
        assert result == expected


class TestProcessPurchaseCommitments:
    def test_process_purchase_commitments(self):
        csv_data = [
            {
                "commitment_id": "commit-123",
                "commitment_date": "2024-08-01T00:00:00Z",
                "cost": "1000.00"
            }
        ]
        
        with patch("anycost_example.read_csv", return_value=csv_data):
            result = process_purchase_commitments("test.csv")
            
        expected = [{
            "lineitem/type": "CommittedUsePurchase",
            "resource/service": "CommittedUse",
            "resource/id": "commit-commit-123",
            "time/usage_start": "2024-08-01T00:00:00Z",
            "cost/cost": "1000.00",
            "cost/discounted_cost": "1000.00"
        }]
        assert result == expected


class TestProcessDiscounts:
    def test_process_discounts(self):
        csv_data = [
            {
                "discount_id": "disc-456",
                "discount_type": "volume-discount",
                "usage_date": "2024-08-16T12:00:00Z",
                "discount": "-25.00"
            }
        ]
        
        with patch("anycost_example.read_csv", return_value=csv_data):
            result = process_discounts("test.csv")
            
        expected = [{
            "lineitem/type": "Discount",
            "resource/service": "volume-discount",
            "resource/id": "discount-disc-456",
            "time/usage_start": "2024-08-16T12:00:00Z",
            "cost/cost": "-25.00",
            "cost/discounted_cost": "-25.00"
        }]
        assert result == expected


class TestWriteCbfRowsToCsv:
    def test_write_cbf_rows_to_csv(self):
        cbf_rows = [
            {
                "lineitem/type": "Usage",
                "resource/service": "compute",
                "resource/id": "instance-123",
                "time/usage_start": "2024-08-16T10:00:00Z",
                "cost/cost": "50.00",
                "cost/discounted_cost": "45.00"
            }
        ]
        
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.csv') as temp_file:
            temp_path = temp_file.name
            
        try:
            write_cbf_rows_to_csv(cbf_rows, temp_path)
            
            with open(temp_path, 'r') as f:
                reader = csv.DictReader(f)
                result = list(reader)
                
            assert len(result) == 1
            assert result[0] == cbf_rows[0]
            
        finally:
            os.unlink(temp_path)


class TestUploadToAnycost:
    @patch('anycost_example.input')
    @patch('anycost_example.getpass.getpass')
    @patch('anycost_example.requests.post')
    @patch('builtins.print')
    def test_upload_to_anycost_success(self, mock_print, mock_post, mock_getpass, mock_input):
        # Setup mocks
        mock_input.side_effect = [
            "connection-123",  # AnyCost Stream Connection ID
            "2024-08",         # month
            "1"                # operation choice (replace_drop)
        ]
        mock_getpass.return_value = "api-key-456"
        
        mock_response = MagicMock()
        mock_response.json.return_value = {"status": "success", "message": "Data uploaded successfully"}
        mock_post.return_value = mock_response
        
        cbf_rows = [{"lineitem/type": "Usage", "cost/cost": "10.00"}]
        
        # Call function
        upload_to_anycost(cbf_rows)
        
        # Verify API call
        mock_post.assert_called_once_with(
            "https://api.cloudzero.com/v2/connections/billing/anycost/connection-123/billing_drops",
            headers={"Authorization": "api-key-456"},
            json={
                "month": "2024-08",
                "operation": "replace_drop", 
                "data": cbf_rows
            }
        )
        
        # Verify response was printed (including operation type prints)
        assert mock_print.call_count == 5
        # Check that the final call was the JSON response
        final_call = mock_print.call_args_list[-1]
        assert '"status": "success"' in str(final_call)

    @patch('anycost_example.input')
    @patch('anycost_example.getpass.getpass')
    @patch('anycost_example.requests.post')
    @patch('builtins.print')
    def test_upload_to_anycost_replace_hourly(self, mock_print, mock_post, mock_getpass, mock_input):
        mock_input.side_effect = [
            "connection-789",
            "2024-09", 
            "2"  # replace_hourly
        ]
        mock_getpass.return_value = "api-key-789"
        
        mock_response = MagicMock()
        mock_response.json.return_value = {"status": "success"}
        mock_post.return_value = mock_response
        
        cbf_rows = []
        upload_to_anycost(cbf_rows)
        
        args, kwargs = mock_post.call_args
        assert kwargs["json"]["operation"] == "replace_hourly"

    @patch('anycost_example.input')
    @patch('anycost_example.getpass.getpass')
    @patch('anycost_example.requests.post')
    @patch('builtins.print')
    def test_upload_to_anycost_sum_operation(self, mock_print, mock_post, mock_getpass, mock_input):
        mock_input.side_effect = [
            "connection-999",
            "2024-10",
            "3"  # sum
        ]
        mock_getpass.return_value = "api-key-999"
        
        mock_response = MagicMock()
        mock_response.json.return_value = {"status": "success"}
        mock_post.return_value = mock_response
        
        cbf_rows = []
        upload_to_anycost(cbf_rows)
        
        args, kwargs = mock_post.call_args
        assert kwargs["json"]["operation"] == "sum"

    @patch('anycost_example.input')
    @patch('anycost_example.getpass.getpass') 
    @patch('anycost_example.requests.post')
    @patch('builtins.print')
    def test_upload_to_anycost_default_operation(self, mock_print, mock_post, mock_getpass, mock_input):
        mock_input.side_effect = [
            "connection-default",
            "2024-11",
            ""  # empty string should default to replace_drop
        ]
        mock_getpass.return_value = "api-key-default"
        
        mock_response = MagicMock()
        mock_response.json.return_value = {"status": "success"}
        mock_post.return_value = mock_response
        
        cbf_rows = []
        upload_to_anycost(cbf_rows)
        
        args, kwargs = mock_post.call_args
        assert kwargs["json"]["operation"] == "replace_drop"