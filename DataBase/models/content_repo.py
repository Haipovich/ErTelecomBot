import logging
from psycopg.rows import class_row

from . import FAQ, HRContact, CompanyContact, ContentRepoData
from .. import get_db_cursor

logger = logging.getLogger(__name__)

class ContentRepository:

    async def get_all_content(self) -> ContentRepoData:
        content = ContentRepoData()
        try:
            async with get_db_cursor(row_factory=class_row(FAQ)) as cur:
                await cur.execute("SELECT * FROM public.faq ORDER BY display_order ASC, id ASC")
                content.faqs = await cur.fetchall() or []

            async with get_db_cursor(row_factory=class_row(HRContact)) as cur:
                await cur.execute("SELECT * FROM public.hr_contacts ORDER BY id ASC")
                content.hr_contacts = await cur.fetchall() or []

            async with get_db_cursor(row_factory=class_row(CompanyContact)) as cur:
                await cur.execute("SELECT * FROM public.company_contacts ORDER BY id ASC")
                content.company_contacts = await cur.fetchall() or []

        except Exception as e:
            logger.error(f"Error loading content data: {e}", exc_info=True)
            return ContentRepoData()
        return content