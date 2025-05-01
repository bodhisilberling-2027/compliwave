#!/usr/bin/env python3
import os
import sys
import time
import json
import logging
import argparse
import requests
import statistics
from concurrent.futures import ThreadPoolExecutor
from typing import List, Dict, Any
from datetime import datetime

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class PerformanceTester:
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.results = {
            "endpoints": {},
            "summary": {
                "total_requests": 0,
                "successful_requests": 0,
                "failed_requests": 0,
                "total_time": 0,
                "average_response_time": 0,
                "min_response_time": float('inf'),
                "max_response_time": 0,
                "response_times": []
            }
        }
    
    def test_endpoint(self, endpoint: str, method: str = "GET", data: Dict = None) -> Dict[str, Any]:
        """Test a single endpoint"""
        url = f"{self.config['BASE_URL']}{endpoint}"
        start_time = time.time()
        
        try:
            if method == "GET":
                response = requests.get(url, headers=self.config['HEADERS'])
            elif method == "POST":
                response = requests.post(url, json=data, headers=self.config['HEADERS'])
            elif method == "PUT":
                response = requests.put(url, json=data, headers=self.config['HEADERS'])
            elif method == "DELETE":
                response = requests.delete(url, headers=self.config['HEADERS'])
            else:
                raise ValueError(f"Unsupported HTTP method: {method}")
            
            response_time = time.time() - start_time
            
            return {
                "status_code": response.status_code,
                "response_time": response_time,
                "success": response.ok,
                "error": None if response.ok else response.text
            }
            
        except Exception as e:
            response_time = time.time() - start_time
            return {
                "status_code": None,
                "response_time": response_time,
                "success": False,
                "error": str(e)
            }
    
    def run_load_test(self, endpoint: str, method: str = "GET", data: Dict = None,
                     num_requests: int = 100, concurrency: int = 10) -> Dict[str, Any]:
        """Run load test for an endpoint"""
        logger.info(f"Running load test for {method} {endpoint}")
        
        endpoint_results = {
            "endpoint": endpoint,
            "method": method,
            "total_requests": num_requests,
            "concurrency": concurrency,
            "response_times": [],
            "status_codes": {},
            "errors": []
        }
        
        with ThreadPoolExecutor(max_workers=concurrency) as executor:
            futures = []
            for _ in range(num_requests):
                futures.append(
                    executor.submit(self.test_endpoint, endpoint, method, data)
                )
            
            for future in futures:
                result = future.result()
                endpoint_results["response_times"].append(result["response_time"])
                
                if result["success"]:
                    status_code = result["status_code"]
                    endpoint_results["status_codes"][status_code] = \
                        endpoint_results["status_codes"].get(status_code, 0) + 1
                else:
                    endpoint_results["errors"].append(result["error"])
        
        # Calculate statistics
        response_times = endpoint_results["response_times"]
        endpoint_results.update({
            "average_response_time": statistics.mean(response_times),
            "median_response_time": statistics.median(response_times),
            "min_response_time": min(response_times),
            "max_response_time": max(response_times),
            "p95_response_time": statistics.quantiles(response_times, n=20)[18],
            "p99_response_time": statistics.quantiles(response_times, n=100)[98],
            "success_rate": (num_requests - len(endpoint_results["errors"])) / num_requests * 100
        })
        
        # Update summary
        self.results["summary"]["total_requests"] += num_requests
        self.results["summary"]["successful_requests"] += \
            num_requests - len(endpoint_results["errors"])
        self.results["summary"]["failed_requests"] += len(endpoint_results["errors"])
        self.results["summary"]["response_times"].extend(response_times)
        
        self.results["endpoints"][endpoint] = endpoint_results
        return endpoint_results
    
    def run_stress_test(self, endpoint: str, method: str = "GET", data: Dict = None,
                       duration: int = 300, concurrency: int = 50) -> Dict[str, Any]:
        """Run stress test for an endpoint"""
        logger.info(f"Running stress test for {method} {endpoint}")
        
        endpoint_results = {
            "endpoint": endpoint,
            "method": method,
            "duration": duration,
            "concurrency": concurrency,
            "response_times": [],
            "status_codes": {},
            "errors": [],
            "requests_per_second": []
        }
        
        start_time = time.time()
        end_time = start_time + duration
        
        with ThreadPoolExecutor(max_workers=concurrency) as executor:
            while time.time() < end_time:
                second_start = time.time()
                futures = []
                
                # Submit requests for this second
                for _ in range(concurrency):
                    futures.append(
                        executor.submit(self.test_endpoint, endpoint, method, data)
                    )
                
                # Collect results
                for future in futures:
                    result = future.result()
                    endpoint_results["response_times"].append(result["response_time"])
                    
                    if result["success"]:
                        status_code = result["status_code"]
                        endpoint_results["status_codes"][status_code] = \
                            endpoint_results["status_codes"].get(status_code, 0) + 1
                    else:
                        endpoint_results["errors"].append(result["error"])
                
                # Calculate requests per second
                second_end = time.time()
                rps = concurrency / (second_end - second_start)
                endpoint_results["requests_per_second"].append(rps)
                
                # Sleep to maintain consistent rate
                time.sleep(max(0, 1 - (second_end - second_start)))
        
        # Calculate statistics
        response_times = endpoint_results["response_times"]
        endpoint_results.update({
            "average_response_time": statistics.mean(response_times),
            "median_response_time": statistics.median(response_times),
            "min_response_time": min(response_times),
            "max_response_time": max(response_times),
            "p95_response_time": statistics.quantiles(response_times, n=20)[18],
            "p99_response_time": statistics.quantiles(response_times, n=100)[98],
            "average_rps": statistics.mean(endpoint_results["requests_per_second"]),
            "max_rps": max(endpoint_results["requests_per_second"]),
            "success_rate": (len(response_times) - len(endpoint_results["errors"])) / len(response_times) * 100
        })
        
        # Update summary
        self.results["summary"]["total_requests"] += len(response_times)
        self.results["summary"]["successful_requests"] += \
            len(response_times) - len(endpoint_results["errors"])
        self.results["summary"]["failed_requests"] += len(endpoint_results["errors"])
        self.results["summary"]["response_times"].extend(response_times)
        
        self.results["endpoints"][endpoint] = endpoint_results
        return endpoint_results
    
    def generate_report(self) -> Dict[str, Any]:
        """Generate performance test report"""
        # Calculate summary statistics
        response_times = self.results["summary"]["response_times"]
        if response_times:
            self.results["summary"].update({
                "average_response_time": statistics.mean(response_times),
                "median_response_time": statistics.median(response_times),
                "min_response_time": min(response_times),
                "max_response_time": max(response_times),
                "p95_response_time": statistics.quantiles(response_times, n=20)[18],
                "p99_response_time": statistics.quantiles(response_times, n=100)[98],
                "success_rate": (self.results["summary"]["successful_requests"] /
                               self.results["summary"]["total_requests"] * 100)
            })
        
        return self.results

def main():
    parser = argparse.ArgumentParser(description="Performance Testing Tool")
    parser.add_argument("--endpoint", required=True, help="API endpoint to test")
    parser.add_argument("--method", default="GET", choices=["GET", "POST", "PUT", "DELETE"],
                       help="HTTP method to use")
    parser.add_argument("--data", help="JSON data for POST/PUT requests")
    parser.add_argument("--type", choices=["load", "stress"], default="load",
                       help="Type of test to run")
    parser.add_argument("--requests", type=int, default=100,
                       help="Number of requests for load test")
    parser.add_argument("--duration", type=int, default=300,
                       help="Duration in seconds for stress test")
    parser.add_argument("--concurrency", type=int, default=10,
                       help="Number of concurrent requests")
    parser.add_argument("--base-url", default="http://localhost:8000",
                       help="Base URL of the API")
    
    args = parser.parse_args()
    
    # Load configuration
    config = {
        "BASE_URL": args.base_url,
        "HEADERS": {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {os.getenv('API_TOKEN', '')}"
        }
    }
    
    # Parse request data if provided
    data = json.loads(args.data) if args.data else None
    
    # Create tester and run test
    tester = PerformanceTester(config)
    
    if args.type == "load":
        results = tester.run_load_test(
            args.endpoint,
            args.method,
            data,
            args.requests,
            args.concurrency
        )
    else:
        results = tester.run_stress_test(
            args.endpoint,
            args.method,
            data,
            args.duration,
            args.concurrency
        )
    
    # Generate and save report
    report = tester.generate_report()
    report_file = f"performance_test_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    
    with open(report_file, "w") as f:
        json.dump(report, f, indent=2)
    
    # Print summary
    print("\nPerformance Test Summary:")
    print(f"Endpoint: {args.endpoint}")
    print(f"Method: {args.method}")
    print(f"Total Requests: {report['summary']['total_requests']}")
    print(f"Successful Requests: {report['summary']['successful_requests']}")
    print(f"Failed Requests: {report['summary']['failed_requests']}")
    print(f"Success Rate: {report['summary']['success_rate']:.2f}%")
    print(f"Average Response Time: {report['summary']['average_response_time']:.3f}s")
    print(f"Median Response Time: {report['summary']['median_response_time']:.3f}s")
    print(f"P95 Response Time: {report['summary']['p95_response_time']:.3f}s")
    print(f"P99 Response Time: {report['summary']['p99_response_time']:.3f}s")
    
    if args.type == "stress":
        print(f"Average RPS: {results['average_rps']:.2f}")
        print(f"Max RPS: {results['max_rps']:.2f}")
    
    print(f"\nDetailed report saved to {report_file}")

if __name__ == "__main__":
    main() 