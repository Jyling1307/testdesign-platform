from sqlalchemy import String, Text, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship

from database import Base


class TestCase(Base):
    __tablename__ = 'testcases_testcase'

    id: Mapped[int] = mapped_column(primary_key=True)
    test_design_id: Mapped[int] = mapped_column(ForeignKey('testdesigns_testdesign.id'))
    name: Mapped[str] = mapped_column(String(500))
    product: Mapped[str] = mapped_column(String(100), default='')
    case_type: Mapped[str] = mapped_column(String(50), default='功能测试')
    phase: Mapped[str] = mapped_column(String(50), default='')
    precondition: Mapped[str] = mapped_column(Text, default='')
    steps: Mapped[str] = mapped_column(Text, default='')
    expected_result: Mapped[str] = mapped_column(Text, default='')
    source_node_path: Mapped[str] = mapped_column(String(1000), default='')

    test_design: Mapped['TestDesign'] = relationship(back_populates='testcases')
