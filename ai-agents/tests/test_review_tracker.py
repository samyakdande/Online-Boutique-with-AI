"""
Test suite for Review Tracker Agent

This test suite validates the functionality of the Review Tracker Agent
including sentiment analysis, fake review detection, and A2A communication.
"""

import asyncio
import pytest
import json
from datetime import datetime
from unittest.mock import Mock, patch, AsyncMock

from ai_agents.agents.review_tracker import (
    ReviewTrackerAgent, 
    ReviewRequest, 
    ReviewAnalysis,
    SentimentType,
    ReviewTheme
)

class TestReviewTrackerAgent:
    """Test cases for Review Tracker Agent"""
    
    @pytest.fixture
    async def agent(self):
        """Create a test agent instance"""
        with patch('ai_agents.agents.review_tracker.genai.configure'):
            with patch('ai_agents.agents.review_tracker.genai.GenerativeModel'):
                agent = ReviewTrackerAgent()
                await agent.start()
                yield agent
                await agent.stop()
    
    @pytest.fixture
    def sample_review_request(self):
        """Sample review request for testing"""
        return ReviewRequest(
            review_text="This product is amazing! Great quality and fast shipping. Highly recommend!",
            product_id="OLJCESPC7Z",
            reviewer_id="user123",
            review_id="review456"
        )
    
    @pytest.fixture
    def mock_gemini_response(self):
        """Mock Gemini AI response"""
        return '''
        {
            "sentiment_score": 0.8,
            "sentiment_type": "positive",
            "authenticity_score": 0.9,
            "key_themes": ["quality", "shipping"],
            "confidence": 0.85,
            "reasoning": "Positive review with specific details about quality and shipping",
            "flagged_for_moderation": false
        }
        '''
    
    @pytest.mark.asyncio
    async def test_agent_initialization(self, agent):
        """Test agent initializes correctly"""
        assert agent.agent_id == "review-tracker"
        assert agent.name == "Review Tracker Agent"
        assert len(agent.capabilities) > 0
        assert agent.review_cache == {}
        assert agent.product_summaries == {}
    
    @pytest.mark.asyncio
    async def test_analyze_review_success(self, agent, sample_review_request, mock_gemini_response):
        """Test successful review analysis"""
        # Mock Gemini API response
        with patch.object(agent, '_get_gemini_analysis', return_value=mock_gemini_response):
            analysis = await agent.analyze_review(sample_review_request)
            
            assert isinstance(analysis, ReviewAnalysis)
            assert analysis.product_id == "OLJCESPC7Z"
            assert analysis.sentiment_type == SentimentType.POSITIVE
            assert analysis.sentiment_score == 0.8
            assert analysis.authenticity_score == 0.9
            assert ReviewTheme.QUALITY in analysis.key_themes
            assert ReviewTheme.SHIPPING in analysis.key_themes
            assert not analysis.flagged_for_moderation
    
    @pytest.mark.asyncio
    async def test_analyze_review_caching(self, agent, sample_review_request, mock_gemini_response):
        """Test that review analysis results are cached"""
        with patch.object(agent, '_get_gemini_analysis', return_value=mock_gemini_response) as mock_gemini:
            # First call
            analysis1 = await agent.analyze_review(sample_review_request)
            
            # Second call with same review
            analysis2 = await agent.analyze_review(sample_review_request)
            
            # Gemini should only be called once due to caching
            assert mock_gemini.call_count == 1
            assert analysis1.sentiment_score == analysis2.sentiment_score
    
    @pytest.mark.asyncio
    async def test_fake_review_detection(self, agent):
        """Test detection of potentially fake reviews"""
        fake_review = ReviewRequest(
            review_text="Great product! Amazing! Best ever! Highly recommend! Five stars!",
            product_id="TEST123",
            review_id="fake_review"
        )
        
        mock_response = '''
        {
            "sentiment_score": 1.0,
            "sentiment_type": "very_positive",
            "authenticity_score": 0.2,
            "key_themes": [],
            "confidence": 0.9,
            "reasoning": "Overly generic positive language with no specific details",
            "flagged_for_moderation": true
        }
        '''
        
        with patch.object(agent, '_get_gemini_analysis', return_value=mock_response):
            with patch.object(agent, '_notify_moderation_needed') as mock_notify:
                analysis = await agent.analyze_review(fake_review)
                
                assert analysis.authenticity_score == 0.2
                assert analysis.flagged_for_moderation
                mock_notify.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_product_summary_update(self, agent, sample_review_request, mock_gemini_response):
        """Test that product summaries are updated correctly"""
        with patch.object(agent, '_get_gemini_analysis', return_value=mock_gemini_response):
            await agent.analyze_review(sample_review_request)
            
            summary = await agent.get_product_review_summary("OLJCESPC7Z")
            
            assert summary is not None
            assert summary.product_id == "OLJCESPC7Z"
            assert summary.total_reviews == 1
            assert summary.average_sentiment == 0.8
            assert summary.authenticity_rate == 0.9
            assert ReviewTheme.QUALITY in summary.top_themes
    
    @pytest.mark.asyncio
    async def test_sentiment_trends(self, agent):
        """Test sentiment trends functionality"""
        trends = await agent.get_sentiment_trends("OLJCESPC7Z", 30)
        
        assert trends["product_id"] == "OLJCESPC7Z"
        assert trends["period_days"] == 30
        assert "trend" in trends
        assert "sentiment_change" in trends
        assert "review_volume_change" in trends
    
    @pytest.mark.asyncio
    async def test_a2a_communication(self, agent, mock_gemini_response):
        """Test A2A protocol message handling"""
        # Test get_product_sentiment request
        message = {
            'request_type': 'get_product_sentiment',
            'data': {'product_id': 'TEST123'}
        }
        
        response = await agent._handle_a2a_request(message)
        assert response['success'] is True
        
        # Test analyze_review request
        message = {
            'request_type': 'analyze_review',
            'data': {
                'review_text': 'Great product!',
                'product_id': 'TEST123'
            }
        }
        
        with patch.object(agent, '_get_gemini_analysis', return_value=mock_gemini_response):
            response = await agent._handle_a2a_request(message)
            assert response['success'] is True
            assert 'data' in response
    
    @pytest.mark.asyncio
    async def test_error_handling(self, agent):
        """Test error handling in review analysis"""
        error_request = ReviewRequest(
            review_text="Test review",
            product_id="ERROR_TEST",
            review_id="error_review"
        )
        
        # Mock Gemini to raise an exception
        with patch.object(agent, '_get_gemini_analysis', side_effect=Exception("API Error")):
            analysis = await agent.analyze_review(error_request)
            
            # Should return a fallback analysis
            assert analysis.product_id == "ERROR_TEST"
            assert analysis.confidence == 0.0
            assert analysis.flagged_for_moderation is True
            assert "Analysis failed" in analysis.reasoning
    
    @pytest.mark.asyncio
    async def test_health_check(self, agent):
        """Test agent health check"""
        with patch.object(agent, '_get_gemini_analysis', return_value="test"):
            health = await agent.health_check()
            
            assert health['agent_id'] == 'review-tracker'
            assert health['status'] in ['healthy', 'degraded']
            assert 'gemini_connection' in health
            assert 'cached_reviews' in health
            assert 'tracked_products' in health
    
    def test_create_analysis_prompt(self, agent):
        """Test analysis prompt creation"""
        review_text = "Great product, love it!"
        prompt = agent._create_analysis_prompt(review_text)
        
        assert review_text in prompt
        assert "sentiment_score" in prompt
        assert "authenticity_score" in prompt
        assert "JSON" in prompt
    
    def test_parse_gemini_response(self, agent, mock_gemini_response):
        """Test parsing of Gemini response"""
        analysis = agent._parse_gemini_response(
            mock_gemini_response, 
            "test_review", 
            "test_product"
        )
        
        assert analysis.review_id == "test_review"
        assert analysis.product_id == "test_product"
        assert analysis.sentiment_score == 0.8
        assert analysis.sentiment_type == SentimentType.POSITIVE
    
    def test_parse_invalid_gemini_response(self, agent):
        """Test parsing of invalid Gemini response"""
        invalid_response = "This is not valid JSON"
        
        analysis = agent._parse_gemini_response(
            invalid_response,
            "test_review",
            "test_product"
        )
        
        # Should return fallback analysis
        assert analysis.confidence == 0.1
        assert analysis.flagged_for_moderation is True
        assert "Failed to parse" in analysis.reasoning

# Integration test
@pytest.mark.asyncio
async def test_full_review_analysis_workflow():
    """Test complete review analysis workflow"""
    with patch('ai_agents.agents.review_tracker.genai.configure'):
        with patch('ai_agents.agents.review_tracker.genai.GenerativeModel'):
            agent = ReviewTrackerAgent()
            await agent.start()
            
            try:
                # Mock multiple reviews for the same product
                reviews = [
                    ReviewRequest(
                        review_text="Excellent quality, fast shipping!",
                        product_id="PROD123",
                        review_id="rev1"
                    ),
                    ReviewRequest(
                        review_text="Good product but sizing runs small",
                        product_id="PROD123", 
                        review_id="rev2"
                    ),
                    ReviewRequest(
                        review_text="Amazing! Best purchase ever! Five stars!",
                        product_id="PROD123",
                        review_id="rev3"
                    )
                ]
                
                mock_responses = [
                    '{"sentiment_score": 0.8, "sentiment_type": "positive", "authenticity_score": 0.9, "key_themes": ["quality", "shipping"], "confidence": 0.85, "reasoning": "Positive with details", "flagged_for_moderation": false}',
                    '{"sentiment_score": 0.3, "sentiment_type": "neutral", "authenticity_score": 0.8, "key_themes": ["sizing"], "confidence": 0.8, "reasoning": "Mixed review with sizing concern", "flagged_for_moderation": false}',
                    '{"sentiment_score": 1.0, "sentiment_type": "very_positive", "authenticity_score": 0.3, "key_themes": [], "confidence": 0.9, "reasoning": "Overly generic positive", "flagged_for_moderation": true}'
                ]
                
                with patch.object(agent, '_get_gemini_analysis', side_effect=mock_responses):
                    # Analyze all reviews
                    analyses = []
                    for review in reviews:
                        analysis = await agent.analyze_review(review)
                        analyses.append(analysis)
                    
                    # Check product summary
                    summary = await agent.get_product_review_summary("PROD123")
                    
                    assert summary.total_reviews == 3
                    assert 0.5 < summary.average_sentiment < 0.8  # Mixed sentiment
                    assert summary.authenticity_rate < 0.8  # One fake review
                    assert len(summary.top_themes) > 0
                    
            finally:
                await agent.stop()

if __name__ == "__main__":
    # Run a simple test
    asyncio.run(test_full_review_analysis_workflow())