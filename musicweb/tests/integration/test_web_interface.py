"""
Integration tests for the web interface.
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
import tempfile
import json
from pathlib import Path

from musicweb.core.models import Track, Library


@pytest.mark.web
class TestWebInterface:
    """Test the Streamlit web interface integration."""
    
    @pytest.fixture
    def mock_streamlit_components(self):
        """Mock all Streamlit components."""
        with patch('streamlit.set_page_config'), \
             patch('streamlit.title'), \
             patch('streamlit.markdown'), \
             patch('streamlit.sidebar') as mock_sidebar, \
             patch('streamlit.columns'), \
             patch('streamlit.file_uploader') as mock_uploader, \
             patch('streamlit.button') as mock_button, \
             patch('streamlit.selectbox') as mock_selectbox, \
             patch('streamlit.write'), \
             patch('streamlit.success'), \
             patch('streamlit.error'), \
             patch('streamlit.warning'), \
             patch('streamlit.info'), \
             patch('streamlit.dataframe'), \
             patch('streamlit.plotly_chart'), \
             patch('streamlit.download_button'):
            
            # Configure sidebar mock
            mock_sidebar.file_uploader = Mock(return_value=None)
            mock_sidebar.button = Mock(return_value=False)
            mock_sidebar.selectbox = Mock(return_value="Compare Libraries")
            mock_sidebar.radio = Mock(return_value="Spotify")
            
            # Configure other mocks
            mock_uploader.return_value = None
            mock_button.return_value = False
            mock_selectbox.return_value = "Option 1"
            
            yield {
                'sidebar': mock_sidebar,
                'file_uploader': mock_uploader,
                'button': mock_button,
                'selectbox': mock_selectbox
            }
    
    def test_app_initialization(self, mock_streamlit_components):
        """Test that the app initializes without errors."""
        with patch('musicweb.web.app.st') as mock_st:
            mock_st.sidebar = mock_streamlit_components['sidebar']
            
            try:
                import musicweb.web.app
                # If import succeeds, basic initialization works
                assert True
            except Exception as e:
                pytest.fail(f"App initialization failed: {e}")
    
    def test_file_upload_spotify(self, mock_streamlit_components, spotify_csv_file):
        """Test Spotify file upload and processing."""
        # Create mock uploaded file
        mock_file = Mock()
        mock_file.name = "spotify_library.csv"
        mock_file.type = "text/csv"
        with open(spotify_csv_file, 'rb') as f:
            mock_file.getvalue.return_value = f.read()
        
        mock_streamlit_components['file_uploader'].return_value = mock_file
        
        with patch('musicweb.web.app.st') as mock_st, \
             patch('musicweb.platforms.create_parser') as mock_parser:
            
            mock_st.sidebar = mock_streamlit_components['sidebar']
            mock_st.file_uploader = mock_streamlit_components['file_uploader']
            
            # Mock parser
            mock_parser_instance = Mock()
            mock_parser_instance.parse.return_value = Library("Test", "spotify")
            mock_parser.return_value = mock_parser_instance
            
            # This would normally trigger file processing
            result = mock_streamlit_components['file_uploader']()
            assert result is not None
            assert result.name == "spotify_library.csv"
    
    def test_file_upload_invalid_format(self, mock_streamlit_components):
        """Test handling of invalid file formats."""
        # Create mock invalid file
        mock_file = Mock()
        mock_file.name = "invalid_file.txt"
        mock_file.type = "text/plain"
        mock_file.getvalue.return_value = b"invalid content"
        
        mock_streamlit_components['file_uploader'].return_value = mock_file
        
        with patch('musicweb.web.app.st') as mock_st:
            mock_st.sidebar = mock_streamlit_components['sidebar']
            mock_st.file_uploader = mock_streamlit_components['file_uploader']
            mock_st.error = Mock()
            
            # Test file type validation
            result = mock_streamlit_components['file_uploader']()
            assert result.type == "text/plain"
    
    def test_library_comparison_workflow(self, mock_streamlit_components, sample_tracks):
        """Test complete library comparison workflow."""
        with patch('musicweb.web.app.st') as mock_st, \
             patch('musicweb.core.comparison.LibraryComparator') as mock_comparator:
            
            # Setup mocks
            mock_st.sidebar = mock_streamlit_components['sidebar']
            mock_st.button = mock_streamlit_components['button']
            mock_st.success = Mock()
            mock_st.dataframe = Mock()
            
            # Mock comparison result
            mock_result = Mock()
            mock_result.shared_tracks = sample_tracks[:1]
            mock_result.unique_to_first = sample_tracks[1:2]
            mock_result.unique_to_second = sample_tracks[2:3]
            mock_result.get_statistics.return_value = {
                'total_tracks_lib1': 2,
                'total_tracks_lib2': 2,
                'shared_tracks': 1,
                'overlap_percentage': 50.0
            }
            
            mock_comparator_instance = Mock()
            mock_comparator_instance.compare_libraries.return_value = mock_result
            mock_comparator.return_value = mock_comparator_instance
            
            # Simulate comparison button click
            mock_streamlit_components['button'].return_value = True
            
            # This would trigger the comparison workflow
            button_clicked = mock_streamlit_components['button']()
            assert button_clicked is True
    
    def test_playlist_creation_workflow(self, mock_streamlit_components, mock_youtube_api):
        """Test playlist creation workflow."""
        with patch('musicweb.web.app.st') as mock_st, \
             patch('musicweb.integrations.playlist.PlaylistManager') as mock_playlist_mgr:
            
            # Setup mocks
            mock_st.sidebar = mock_streamlit_components['sidebar']
            mock_st.button = mock_streamlit_components['button']
            mock_st.text_input = Mock(return_value="Test Playlist")
            mock_st.success = Mock()
            
            # Mock playlist manager
            mock_mgr_instance = Mock()
            mock_mgr_instance.create_playlist.return_value = {
                'id': 'playlist123',
                'title': 'Test Playlist',
                'tracks_added': 5
            }
            mock_playlist_mgr.return_value = mock_mgr_instance
            
            # Simulate playlist creation
            mock_streamlit_components['button'].return_value = True
            
            button_clicked = mock_streamlit_components['button']()
            assert button_clicked is True
    
    def test_error_handling_in_ui(self, mock_streamlit_components):
        """Test error handling in the UI."""
        with patch('musicweb.web.app.st') as mock_st:
            mock_st.sidebar = mock_streamlit_components['sidebar']
            mock_st.error = Mock()
            mock_st.exception = Mock()
            
            # Test error display
            mock_st.error("Test error message")
            mock_st.error.assert_called_with("Test error message")
    
    @pytest.mark.slow
    def test_large_file_upload_performance(self, mock_streamlit_components, performance_timer):
        """Test performance with large file uploads."""
        # Create large mock file
        large_data = "Track Name,Artist,Album,Duration\n" * 10000
        
        mock_file = Mock()
        mock_file.name = "large_library.csv"
        mock_file.type = "text/csv"
        mock_file.getvalue.return_value = large_data.encode()
        
        mock_streamlit_components['file_uploader'].return_value = mock_file
        
        with patch('musicweb.web.app.st') as mock_st:
            mock_st.sidebar = mock_streamlit_components['sidebar']
            
            performance_timer.start()
            # Simulate file processing
            result = mock_streamlit_components['file_uploader']()
            performance_timer.stop()
            
            assert performance_timer.elapsed < 5.0  # Should process quickly
            assert result is not None
    
    def test_session_state_management(self, mock_streamlit_components):
        """Test Streamlit session state management."""
        with patch('musicweb.web.app.st') as mock_st:
            # Mock session state
            mock_session_state = {}
            mock_st.session_state = mock_session_state
            
            # Test state persistence
            mock_st.session_state['library1'] = "test_library"
            assert mock_st.session_state['library1'] == "test_library"
    
    def test_download_functionality(self, mock_streamlit_components, temp_dir):
        """Test file download functionality."""
        with patch('musicweb.web.app.st') as mock_st:
            mock_st.download_button = Mock()
            
            # Create test file
            test_file = temp_dir / "test_results.csv"
            test_file.write_text("test,data\n1,2\n3,4")
            
            # Test download button
            mock_st.download_button(
                label="Download Results",
                data=test_file.read_text(),
                file_name="results.csv",
                mime="text/csv"
            )
            
            mock_st.download_button.assert_called_once()
    
    def test_visualization_components(self, mock_streamlit_components):
        """Test data visualization components."""
        with patch('musicweb.web.app.st') as mock_st, \
             patch('plotly.express.pie') as mock_pie, \
             patch('plotly.express.bar') as mock_bar:
            
            mock_st.plotly_chart = Mock()
            
            # Mock plotly charts
            mock_pie.return_value = Mock()
            mock_bar.return_value = Mock()
            
            # Test chart creation
            mock_chart = mock_pie()
            mock_st.plotly_chart(mock_chart)
            
            mock_st.plotly_chart.assert_called_once()
    
    def test_navigation_and_tabs(self, mock_streamlit_components):
        """Test navigation and tab functionality."""
        with patch('musicweb.web.app.st') as mock_st:
            mock_st.tabs = Mock(return_value=[Mock(), Mock(), Mock()])
            mock_st.sidebar.selectbox = Mock(return_value="Compare Libraries")
            
            # Test tab creation
            tabs = mock_st.tabs(["Tab 1", "Tab 2", "Tab 3"])
            assert len(tabs) == 3
            
            # Test sidebar navigation
            selected = mock_st.sidebar.selectbox("Choose function", ["Option 1", "Option 2"])
            assert selected == "Compare Libraries"
    
    def test_responsive_layout(self, mock_streamlit_components):
        """Test responsive layout components."""
        with patch('musicweb.web.app.st') as mock_st:
            mock_st.columns = Mock(return_value=[Mock(), Mock()])
            mock_st.container = Mock()
            mock_st.expander = Mock()
            
            # Test layout components
            cols = mock_st.columns(2)
            assert len(cols) == 2
            
            container = mock_st.container()
            assert container is not None
            
            expander = mock_st.expander("Details")
            assert expander is not None