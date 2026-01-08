from typing import Annotated, Optional
from sqlalchemy.orm import declarative_base, Mapped, mapped_column
from sqlalchemy import String, Integer, Text, Boolean, DateTime, Enum as SQLEnum
from datetime import datetime
from uuid import uuid4
from enum import StrEnum

ID = Annotated[str, mapped_column(String, 
                                    primary_key=True,
                                    index=True,
                                    default=uuid4)]
URL = Annotated[str, mapped_column(String, 
                                    nullable=False,  
                                    index=True)]
TextContent = Annotated[str, mapped_column(Text)]
TimeStamp = Annotated[datetime, mapped_column(DateTime, 
                                    nullable=False, 
                                    default=datetime.now)]

# для полей, которые могут быть NULL
OptionalURL = Annotated[Optional[str], mapped_column(String, 
                                                    nullable=True, 
                                                    index=True)]
OptionalText = Annotated[Optional[str], mapped_column(Text, 
                                                    nullable=True)]

class PostStatus(StrEnum):
    NEW = 'new'
    # 'if need' TRANSLATED = 'translated'
    GENERATED = 'generated'
    PUBLISHED = 'published'
    FAILED = 'failed'


class SourceType(StrEnum):
    SITE = 'site'
    TG = 'tg'

