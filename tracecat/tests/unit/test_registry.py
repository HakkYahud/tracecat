import os
import textwrap

import pytest
from tracecat_registry import RegistryValidationError

from tracecat.registry.repository import Repository


@pytest.fixture
def mock_package(tmp_path):
    """Pytest fixture that creates a mock package with files and cleans up after the test."""
    import sys
    from importlib.machinery import ModuleSpec
    from types import ModuleType

    # Create a new module
    test_module = ModuleType("test_module")

    # Create a module spec for the test module
    module_spec = ModuleSpec("test_module", None)
    test_module.__spec__ = module_spec
    # Set __path__ to the temporary directory
    test_module.__path__ = [str(tmp_path)]

    try:
        # Add the module to sys.modules
        sys.modules["test_module"] = test_module
        # Create a file for the sync function
        with open(os.path.join(tmp_path, "sync_function.py"), "w") as f:
            f.write(
                textwrap.dedent(
                    """
                from tracecat_registry import registry

                @registry.register(
                    description="This is a test function",
                    namespace="test",
                )
                def test_function(num: int) -> int:
                    return num
            """
                )
            )

        # Create a file for the async function
        with open(os.path.join(tmp_path, "async_function.py"), "w") as f:
            f.write(
                textwrap.dedent(
                    """
                from tracecat_registry import registry

                @registry.register(
                    description="This is an async test function",
                    namespace="test",
                )
                async def async_test_function(num: int) -> int:
                    return num
            """
                )
            )

        yield test_module
    finally:
        # Clean up
        del sys.modules["test_module"]


def test_udf_validate_args(mock_package):
    """This tests the UDF.validate_args method, which shouldn't raise any exceptions
    when given a templated expression.
    """
    # Register UDFs from the mock package
    repo = Repository()
    repo._register_udfs_from_package(mock_package)

    # Get the registered UDF
    udf = repo.get("test.test_function")

    # Test the UDF
    udf.validate_args(num="${{ path.to.number }}")
    udf.validate_args(num=1)
    with pytest.raises(RegistryValidationError):
        udf.validate_args(num="not a number")


def test_registry_function_can_be_called(mock_package):
    """We need to test that the ordering of the workflow tasks is correct."""
    repo = Repository()
    assert len(repo) == 0

    repo._register_udfs_from_package(mock_package)
    udf = repo.get("test.test_function")
    for i in range(10):
        assert udf.fn(num=i) == i


@pytest.mark.anyio
async def test_registry_async_function_can_be_called(mock_package):
    repo = Repository()
    assert len(repo) == 0

    repo._register_udfs_from_package(mock_package)
    udf = repo.get("test.async_test_function")
    for i in range(10):
        assert await udf.fn(num=i) == i