"""Tests for Production and Scale Readiness — Phase 8."""

from case_core.production import (
    CircuitBreaker,
    DeploymentConfig,
    DeploymentEnvironment,
    HealthCheck,
    HealthChecker,
    HealthStatus,
    LoadBalancer,
    MetricType,
    PerformanceMetric,
    PerformanceMonitor,
    ProductionReadiness,
    RateLimiter,
)


class TestCircuitBreaker:
    def test_record_success(self):
        cb = CircuitBreaker(failure_threshold=3)
        cb.record_failure()
        cb.record_failure()
        cb.record_success()
        assert cb.is_open() is False

    def test_record_failure_threshold(self):
        cb = CircuitBreaker(failure_threshold=3)
        cb.record_failure()
        cb.record_failure()
        cb.record_failure()
        assert cb.is_open() is True

    def test_get_state(self):
        cb = CircuitBreaker(failure_threshold=5)
        state = cb.get_state()
        assert state["failure_count"] == 0
        assert state["is_open"] is False


class TestRateLimiter:
    def test_allow_request(self):
        limiter = RateLimiter(max_requests_per_second=10)
        assert limiter.allow_request() is True

    def test_rate_limit_exceeded(self):
        limiter = RateLimiter(max_requests_per_second=2)
        limiter.allow_request()
        limiter.allow_request()
        assert limiter.allow_request() is False

    def test_reset(self):
        limiter = RateLimiter(max_requests_per_second=1)
        limiter.allow_request()
        limiter.reset()
        assert limiter.allow_request() is True

    def test_get_usage(self):
        limiter = RateLimiter(max_requests_per_second=100)
        limiter.allow_request()
        usage = limiter.get_usage()
        assert usage["current_requests"] == 1


class TestLoadBalancer:
    def test_get_next_instance(self):
        lb = LoadBalancer(["a", "b", "c"])
        assert lb.get_next_instance() == "a"
        assert lb.get_next_instance() == "b"
        assert lb.get_next_instance() == "c"
        assert lb.get_next_instance() == "a"

    def test_get_status(self):
        lb = LoadBalancer(["a", "b"])
        status = lb.get_status()
        assert status["total_instances"] == 2


class TestPerformanceMonitor:
    def test_record_metric(self):
        monitor = PerformanceMonitor()
        metric = monitor.record_metric("request_duration", MetricType.GAUGE, 150.0, "ms")
        assert metric.name == "request_duration"
        assert metric.value == 150.0

    def test_get_metrics(self):
        monitor = PerformanceMonitor()
        monitor.record_metric("req_1", MetricType.GAUGE, 1.0)
        monitor.record_metric("req_2", MetricType.GAUGE, 2.0)
        assert len(monitor.get_metrics()) == 2

    def test_get_metrics_by_name(self):
        monitor = PerformanceMonitor()
        monitor.record_metric("duration", MetricType.GAUGE, 100.0)
        monitor.record_metric("count", MetricType.COUNTER, 1.0)
        duration_metrics = monitor.get_metrics("duration")
        assert len(duration_metrics) == 1

    def test_get_summary(self):
        monitor = PerformanceMonitor()
        monitor.record_metric("m1", MetricType.GAUGE, 1.0)
        summary = monitor.get_summary()
        assert summary["total_metrics"] == 1


class TestHealthChecker:
    def test_check_component(self):
        checker = HealthChecker()
        check = checker.check_component("api", HealthStatus.HEALTHY, "OK", 10.0)
        assert check.component == "api"
        assert check.status == HealthStatus.HEALTHY

    def test_get_health_status_healthy(self):
        checker = HealthChecker()
        checker.check_component("api", HealthStatus.HEALTHY, "OK")
        status = checker.get_health_status()
        assert status["status"] == "healthy"

    def test_get_health_status_unhealthy(self):
        checker = HealthChecker()
        checker.check_component("api", HealthStatus.HEALTHY, "OK")
        checker.check_component("db", HealthStatus.UNHEALTHY, "Down")
        status = checker.get_health_status()
        assert status["status"] == "unhealthy"

    def test_get_health_status_degraded(self):
        checker = HealthChecker()
        checker.check_component("api", HealthStatus.HEALTHY, "OK")
        checker.check_component("cache", HealthStatus.DEGRADED, "Slow")
        status = checker.get_health_status()
        assert status["status"] == "degraded"

    def test_get_health_status_empty(self):
        checker = HealthChecker()
        status = checker.get_health_status()
        assert status["status"] == "unknown"


class TestProductionReadiness:
    def test_get_readiness_status(self):
        pr = ProductionReadiness()
        status = pr.get_readiness_status()
        assert status["environment"] == "production"
        assert status["replicas"] == 3

    def test_simulate_load(self):
        pr = ProductionReadiness(DeploymentConfig(rate_limit_per_second=5))
        result = pr.simulate_load(10)
        assert result["total_requests"] == 10
        assert result["allowed"] == 5
        assert result["rejected"] == 5

    def test_perform_health_check(self):
        pr = ProductionReadiness()
        health = pr.perform_health_check()
        assert health["status"] == "healthy"
        assert len(health["components"]) == 3

    def test_record_performance(self):
        pr = ProductionReadiness()
        metric = pr.record_performance("response_time", 150.0, "ms")
        assert metric.name == "response_time"


class TestEnums:
    def test_deployment_environments(self):
        assert DeploymentEnvironment.DEVELOPMENT.value == "development"
        assert DeploymentEnvironment.PRODUCTION.value == "production"

    def test_health_status(self):
        assert HealthStatus.HEALTHY.value == "healthy"
        assert HealthStatus.UNHEALTHY.value == "unhealthy"

    def test_metric_type(self):
        assert MetricType.COUNTER.value == "counter"
        assert MetricType.HISTOGRAM.value == "histogram"


class TestModels:
    def test_deployment_config_defaults(self):
        config = DeploymentConfig()
        assert config.environment == DeploymentEnvironment.PRODUCTION
        assert config.replicas == 3
        assert config.max_workers == 4

    def test_performance_metric_creation(self):
        metric = PerformanceMetric(
            name="test",
            metric_type=MetricType.GAUGE,
            value=42.0,
            unit="count",
        )
        assert metric.name == "test"
        assert metric.tags == {}

    def test_health_check_creation(self):
        check = HealthCheck(
            component="test",
            status=HealthStatus.HEALTHY,
            message="OK",
            latency_ms=10.0,
        )
        assert check.component == "test"
        assert check.latency_ms == 10.0
