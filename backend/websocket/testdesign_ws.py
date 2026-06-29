"""WebSocket endpoints for test design generation and refinement."""

import json
from fastapi import WebSocket, WebSocketDisconnect
from sqlalchemy.orm import Session

from deps import get_db
from models.testdesign import TestDesign, DesignReview
from llm.client import stream_chat
from llm.prompts.generate_design import build_generate_prompt
from llm.prompts.refine_design import build_refine_prompt
from services.testdesign_service import collect_kb_context


async def websocket_generate(websocket: WebSocket, design_id: int):
    """WebSocket endpoint for streaming test design generation.

    🚀 4-step RAG pipeline（从 langchain 迁移 + 批量 Q2E 优化）：
    1. 提取测试点（1 次 LLM）
    2. 批量扩写检索问题（1 次 LLM）★ 替代 langchain 的 N 次串行
    3. 多源检索 + few-shot（0 次 LLM）
    4. 流式生成测试设计（1 次 LLM 流式）
    总计 3 次 LLM 调用，比 langchain 的 N+2 次快 10 倍+。
    """
    from rag.pipeline.orchestrator import (
        extract_test_points, expand_to_queries, retrieve_context, stream_generate_design_md,
    )

    await websocket.accept()

    db: Session = next(get_db())
    try:
        design = db.get(TestDesign, design_id)
        if not design:
            await websocket.send_json({'type': 'error', 'message': '测试设计不存在'})
            await websocket.close()
            return

        # Receive generation params
        data = await websocket.receive_text()
        params = json.loads(data)
        notes = params.get('notes', '')
        test_types = params.get('test_types', None)

        design.status = 'generating'
        db.commit()

        doc = design.document
        document_text = doc.raw_text or ''

        # 步骤1：提取测试点
        await websocket.send_json({'type': 'status', 'message': '正在提取测试点...'})
        test_points = extract_test_points(document_text)
        if not test_points:
            # 提取失败回退：用文档开头作为单一测试点
            test_points = [document_text[:200] or '（文档为空）']

        # 步骤2：批量扩写检索问题（★核心优化：1 次 LLM 替代 N 次）
        await websocket.send_json({'type': 'status', 'message': '正在扩写检索问题...'})
        queries = expand_to_queries(test_points)

        # 步骤3：多源检索 + few-shot（纯向量检索，0 次 LLM）
        await websocket.send_json({'type': 'status', 'message': '正在检索知识库...'})
        retrieved = retrieve_context(queries)

        # 步骤4：流式生成测试设计
        await websocket.send_json({'type': 'status', 'message': 'AI 正在生成测试设计...'})
        full_response = ''
        async for chunk in stream_generate_design_md(
            test_points=test_points,
            context=retrieved['context'],
            few_shot=retrieved['few_shot'],
            document_text=document_text,
            notes=notes,
            test_types=test_types,
        ):
            full_response += chunk
            await websocket.send_json({'type': 'chunk', 'content': chunk})

        # Save result
        design.full_md = full_response
        design.status = 'reviewing'
        db.commit()

        await websocket.send_json({'type': 'markdown', 'content': full_response})
        await websocket.send_json({'type': 'done'})

    except WebSocketDisconnect:
        pass
    except Exception as e:
        await websocket.send_json({'type': 'error', 'message': str(e)})
    finally:
        db.close()


async def websocket_refine(websocket: WebSocket, design_id: int):
    """WebSocket endpoint for streaming test design refinement."""
    await websocket.accept()

    db: Session = next(get_db())
    try:
        design = db.get(TestDesign, design_id)
        if not design:
            await websocket.send_json({'type': 'error', 'message': '测试设计不存在'})
            await websocket.close()
            return

        # Receive refinement params
        data = await websocket.receive_text()
        params = json.loads(data)
        feedback = params.get('feedback', '')
        rejected_nodes = params.get('rejected_nodes', [])
        test_types = params.get('test_types', None)

        # Get rejected reviews from DB
        if not rejected_nodes:
            reviews = db.query(DesignReview).filter(
                DesignReview.test_design_id == design_id,
                DesignReview.status == 'rejected',
            ).all()
            rejected_nodes = [
                {'node_path': r.node_path, 'node_text': r.node_text, 'feedback': r.feedback}
                for r in reviews
            ]

        design.status = 'generating'
        db.commit()

        await websocket.send_json({'type': 'status', 'message': 'AI 正在优化测试设计...'})

        # Build prompt
        system_prompt, user_message = build_refine_prompt(
            current_md=design.full_md,
            rejected_nodes=rejected_nodes,
            feedback_text=feedback,
            test_types=test_types,
        )

        # Stream response
        full_response = ''
        async for chunk in stream_chat(system_prompt, user_message):
            full_response += chunk
            await websocket.send_json({'type': 'chunk', 'content': chunk})

        # Save result
        design.full_md = full_response
        design.version += 1
        design.status = 'reviewing'
        db.commit()

        await websocket.send_json({'type': 'markdown', 'content': full_response})
        await websocket.send_json({'type': 'done'})

    except WebSocketDisconnect:
        pass
    except Exception as e:
        await websocket.send_json({'type': 'error', 'message': str(e)})
    finally:
        db.close()
