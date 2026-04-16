# Copyright (c) 2025 Kirk Lin
# SPDX-License-Identifier: MIT

import json
import logging
import requests
from typing import List, Dict, Optional
from langchain_core.tools import tool
from langchain_core.messages import HumanMessage
from src.llms.llm import get_llm_by_type

logger = logging.getLogger(__name__)


class WebContentExtractor:
    """Custom web content extraction utility following Kairos patterns."""

    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        })

    def fetch_content(self, url: str) -> Dict[str, str]:
        """Fetch and extract content from a URL."""
        try:
            response = self.session.get(url, timeout=15)
            response.raise_for_status()

            from bs4 import BeautifulSoup

            soup = BeautifulSoup(response.content, 'html.parser')

            for element in soup(['script', 'style', 'nav', 'header', 'footer', 'aside', 'advertisement']):
                element.decompose()

            title_tag = soup.find('title')
            title = title_tag.get_text().strip() if title_tag else "No Title"

            main_content = ""

            content_selectors = [
                'main', 'article', '[role="main"]',
                '.content', '#content', '.post-content',
                '.entry-content', '.article-content'
            ]

            for selector in content_selectors:
                content_elem = soup.select_one(selector)
                if content_elem:
                    main_content = content_elem.get_text(separator='\n', strip=True)
                    break

            if not main_content:
                body = soup.find('body')
                if body:
                    main_content = body.get_text(separator='\n', strip=True)

            lines = [line.strip() for line in main_content.split('\n') if line.strip()]
            main_content = '\n'.join(lines)

            return {
                'title': title,
                'content': main_content[:10000],  # Limit content size
                'url': url,
                'status': 'success'
            }

        except Exception as e:
            logger.error(f"Error extracting content from {url}: {e}")
            return {
                'title': f"Error: {url}",
                'content': f"Failed to extract content: {str(e)}",
                'url': url,
                'status': 'error'
            }


class SearchEngine:
    """Custom search implementation compatible with Kairos."""

    def search(self, query: str, num_results: int = 5) -> List[Dict[str, str]]:
        """Search for information and return structured results."""
        try:
            search_url = "https://api.duckduckgo.com/"
            params = {
                'q': query,
                'format': 'json',
                'no_redirect': '1',
                'no_html': '1',
                'skip_disambig': '1'
            }

            response = requests.get(search_url, params=params, timeout=10)
            data = response.json()

            results = []

            # Get abstract if available
            if data.get('Abstract'):
                results.append({
                    'title': data.get('Heading', query),
                    'url': data.get('AbstractURL', ''),
                    'snippet': data.get('Abstract', ''),
                    'source': 'DuckDuckGo Abstract'
                })

            for topic in data.get('RelatedTopics', [])[:num_results - 1]:
                if isinstance(topic, dict) and topic.get('Text'):
                    results.append({
                        'title': topic.get('Text', '')[:100] + '...',
                        'url': topic.get('FirstURL', ''),
                        'snippet': topic.get('Text', ''),
                        'source': 'DuckDuckGo Related'
                    })

            if not results:
                results = self._fallback_html_search(query, num_results)

            return results[:num_results]

        except Exception as e:
            logger.error(f"Search error for '{query}': {e}")
            return self._fallback_html_search(query, num_results)

    def _fallback_html_search(self, query: str, num_results: int) -> List[Dict[str, str]]:
        """Fallback HTML scraping method."""
        try:
            search_url = "https://duckduckgo.com/html/"
            params = {'q': query}
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            }

            response = requests.get(search_url, params=params, headers=headers, timeout=10)

            from bs4 import BeautifulSoup
            soup = BeautifulSoup(response.content, 'html.parser')

            results = []
            links = soup.find_all('a', class_='result__a')[:num_results]

            for link in links:
                title = link.get_text().strip()
                href = link.get('href', '')

                result_container = link.find_parent('div', class_='result')
                snippet_elem = result_container.find('a', class_='result__snippet') if result_container else None
                snippet = snippet_elem.get_text().strip() if snippet_elem else ""

                results.append({
                    'title': title,
                    'url': href,
                    'snippet': snippet,
                    'source': 'DuckDuckGo HTML'
                })

            return results

        except Exception as e:
            logger.error(f"Fallback search error: {e}")
            return []


class ReportGenerator:
    """Generate structured reports following our Kairos LLM patterns."""

    def __init__(self, llm_type: str = "reasoning"):
        self.llm_type = llm_type

    def create_report(self, data: str, topic: str, report_style: str = "professional") -> str:
        """Generate a formatted report from research data."""

        style_prompts = {
            "professional": """Create a professional research report with clear structure:
                - **Title**: Clear, descriptive title
                - **Key Points**: 3-5 bullet points with the most important facts
                - **Overview**: Background context and significance
                - **Detailed Analysis**: In-depth information organized logically
                Use markdown formatting and include specific data points.""",

            "comparison": """Create a comparative analysis report with structure:
                - **Title**: "X vs. Y: A Comparative Analysis of [Focus Area]"
                - **Key Points**: Bullet points highlighting main differences and similarities
                - **Overview**: Background context for both subjects
                - **Detailed Analysis**: Separate sections for each subject with specifics
                Focus on quantifiable differences and concrete facts.""",

            "summary": """Create a concise summary report with:
                - **Title**: Clear topic title
                - **Key Points**: Main findings in bullet format
                - **Important Details**: Critical information organized clearly
                - **Key Takeaways**: Bottom-line conclusions
                Keep it comprehensive but concise."""
        }

        style_instruction = style_prompts.get(report_style, style_prompts["professional"])

        prompt = f"""You are a professional research analyst. Based on the research data provided, {style_instruction}

Topic: {topic}

Research Data:
{data}

Requirements:
- Use markdown formatting with proper headers
- Include specific facts, numbers, dates, and measurements
- Make it well-structured and scannable
- Focus on accuracy and clarity
- Cite key information sources when possible
- Keep the professional tone consistent with research reports

Generate the complete report now:"""

        try:
            llm = get_llm_by_type(self.llm_type)
            response = llm.invoke([HumanMessage(content=prompt)])
            return response.content
        except Exception as e:
            logger.error(f"Report generation error: {e}")
            return f"Error generating report: {str(e)}"


# Initialize utility classes
extractor = WebContentExtractor()
search_engine = SearchEngine()
report_gen = ReportGenerator()


@tool
def fetch_webpage_content(url: str) -> str:
    """
    Fetch and extract clean content from a webpage.

    Args:
        url: The webpage URL to fetch content from

    Returns:
        Extracted content in a readable format
    """
    try:
        content_data = extractor.fetch_content(url)

        if content_data['status'] == 'error':
            return f"Error fetching {url}: {content_data['content']}"

        return f"""# {content_data['title']}
**Source:** {content_data['url']}

{content_data['content']}"""
    except Exception as e:
        logger.error(f"Error in fetch_webpage_content: {e}")
        return f"Error fetching webpage content: {str(e)}"


@tool
def search_web_information(query: str, max_results: int = 5) -> str:
    """
    Search the web for information on a specific topic.

    Args:
        query: Search query
        max_results: Maximum number of results to return (default: 5)

    Returns:
        Formatted search results with titles, URLs, and snippets
    """
    try:
        results = search_engine.search(query, max_results)

        if not results:
            return f"No search results found for: {query}"

        formatted_results = [f"# Search Results for: {query}\n"]

        for i, result in enumerate(results, 1):
            formatted_results.append(f"""
## {i}. {result['title']}
**URL:** {result['url']}
**Summary:** {result['snippet']}
**Source:** {result.get('source', 'Web Search')}
""")

        return "\n".join(formatted_results)
    except Exception as e:
        logger.error(f"Error in search_web_information: {e}")
        return f"Error performing web search: {str(e)}"


@tool
def generate_research_report(research_data: str, topic: str, style: str = "professional") -> str:
    """
    Generate a structured report from collected research data.

    Args:
        research_data: The collected research information
        topic: Main topic of the report
        style: Report style - "professional", "comparison", or "summary"

    Returns:
        Well-formatted research report in markdown
    """
    try:
        return report_gen.create_report(research_data, topic, style)
    except Exception as e:
        logger.error(f"Error in generate_research_report: {e}")
        return f"Error generating report: {str(e)}"


@tool
def comprehensive_topic_research(topic: str, include_sources: Optional[List[str]] = None) -> str:
    """
    Conduct comprehensive research on a topic using multiple approaches.

    Args:
        topic: The topic to research thoroughly
        include_sources: Optional list of specific URLs to include in research

    Returns:
        Comprehensive research compilation with final report
    """
    try:
        logger.info(f"Starting comprehensive research on: {topic}")
        research_data = []

        logger.info("Performing web search...")
        search_results = search_engine.search(f"{topic} comprehensive information facts", 5)

        if search_results:
            search_text = f"# Search Results for: {topic}\n\n"
            for i, result in enumerate(search_results, 1):
                search_text += f"## {i}. {result['title']}\n**URL:** {result['url']}\n**Summary:** {result['snippet']}\n\n"
            research_data.append(search_text)

        search_queries = [
            f"{topic} details specifications",
            f"{topic} current status 2025",
            f"{topic} market trends analysis"
        ]

        for query in search_queries:
            additional_results = search_engine.search(query, 2)
            if additional_results:
                query_text = f"\n## Additional Search: {query}\n"
                for result in additional_results:
                    query_text += f"- **{result['title']}**: {result['snippet']}\n"
                research_data.append(query_text)

        if include_sources:
            logger.info(f"Fetching content from {len(include_sources)} specific sources...")
            for url in include_sources:
                try:
                    content_data = extractor.fetch_content(url)
                    if content_data['status'] == 'success':
                        research_data.append(
                            f"\n## Detailed Source Analysis\n**{content_data['title']}**\nSource: {content_data['url']}\n\n{content_data['content'][:1000]}...")
                except Exception as e:
                    logger.warning(f"Failed to fetch {url}: {e}")

        combined_research = "\n\n".join(research_data)

        logger.info("Generating final research report...")
        final_report = report_gen.create_report(
            combined_research,
            topic,
            "professional"
        )

        return final_report
    except Exception as e:
        logger.error(f"Error in comprehensive_topic_research: {e}")
        return f"Error conducting comprehensive research: {str(e)}"


@tool
def compare_topics(topic1: str, topic2: str, focus_areas: Optional[List[str]] = None) -> str:
    """
    Research and compare two topics across specified areas.

    Args:
        topic1: First topic to compare
        topic2: Second topic to compare
        focus_areas: Specific areas to focus the comparison on (e.g., ["height", "construction"])

    Returns:
        Detailed comparison report in the style of your example images
    """
    try:
        logger.info(f"Starting comparison research: {topic1} vs {topic2}")

        focus_text = f" {' '.join(focus_areas)}" if focus_areas else ""

        logger.info(f"Researching {topic1}...")
        topic1_queries = [
            f"{topic1} facts details specifications{focus_text}",
            f"{topic1} measurements dimensions{focus_text}",
            f"{topic1} history construction{focus_text}"
        ]

        topic1_data = []
        for query in topic1_queries:
            result = search_web_information(query, 3)
            topic1_data.append(result)

        logger.info(f"Researching {topic2}...")
        topic2_queries = [
            f"{topic2} facts details specifications{focus_text}",
            f"{topic2} measurements dimensions{focus_text}",
            f"{topic2} history construction{focus_text}"
        ]

        topic2_data = []
        for query in topic2_queries:
            result = search_web_information(query, 3)
            topic2_data.append(result)

        combined_data = f"""
# Research Data for {topic1}
{' '.join(topic1_data)}

# Research Data for {topic2}  
{' '.join(topic2_data)}

# Focus Areas for Comparison
{focus_areas if focus_areas else ['general comparison', 'key characteristics', 'significance']}
"""

        logger.info("Generating comparison report...")
        comparison_report = generate_research_report(
            combined_data,
            f"{topic1} vs {topic2}",
            "comparison"
        )

        return comparison_report
    except Exception as e:
        logger.error(f"Error in compare_topics: {e}")
        return f"Error creating comparison: {str(e)}"


@tool
def extract_key_facts(content: str, topic: str, fact_count: int = 5) -> str:
    """
    Extract key facts and figures from content about a specific topic.

    Args:
        content: The content to analyze
        topic: The topic to focus on
        fact_count: Number of key facts to extract

    Returns:
        Extracted key facts in structured format
    """
    try:
        extraction_prompt = f"""From the following content about {topic}, extract the {fact_count} most important and specific facts. Focus on:
- Quantifiable information (measurements, dates, statistics)
- Concrete details and specifications  
- Historical facts and milestones
- Current status and recent developments

Content:
{content[:5000]}  

Format your response as a numbered list with specific details:
1. [Fact with numbers/dates/specifics]
2. [Fact with numbers/dates/specifics]
etc.

Be precise and include actual measurements, dates, and figures wherever possible."""

        llm = get_llm_by_type("reasoning")
        response = llm.invoke([HumanMessage(content=extraction_prompt)])

        return f"# Key Facts about {topic}\n\n{response.content}"

    except Exception as e:
        logger.error(f"Error extracting key facts: {e}")
        return f"Error extracting facts: {str(e)}"
