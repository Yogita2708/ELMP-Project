import pytest
from app import app, init_db

# Use pytest fixture to set up and tear down a test client
@pytest.fixture
def client():
    # Use the app context for testing
    app.config['TESTING'] = True
    with app.test_client() as client:
        yield client

def test_index_redirect(client):
    """Test the base route redirects to the dashboard."""
    # The base route should redirect to the dashboard
    response = client.get('/', follow_redirects=True)
    assert response.status_code == 200
    # Check if the title of the dashboard is in the response data
    assert b"Employee Leave Portal - Dashboard" in response.data

def test_db_initialization():
    """Test that the init_db function runs without errors."""
    try:
        init_db()
        assert True
    except Exception as e:
        pytest.fail(f"init_db failed with error: {e}")

# NOTE: You would add more comprehensive tests here for:
# - Leave submission validation
# - Admin approval/rejection logic
# - Balance deduction after approval
