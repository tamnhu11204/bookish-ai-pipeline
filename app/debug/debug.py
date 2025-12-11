# app/debug/chains_debug.py
import json
from pprint import pprint
from app.chains.behavioral_chain import chain as behavioral_chain
from app.chains.collaborative_chain import collaborative_chain
from app.chains.trending_chain import trending_chain
from app.chains.master_chain import master_chain

USER_ID = "6919e29af94cd5bf68e521cd"  # đổi thành user bạn muốn test


def debug_behavioral():
    print("\n===[1/4] DEBUG BEHAVIORAL CHAIN===".center(80, "="))
    result = behavioral_chain.invoke(
        {"user_id": USER_ID}, config={"callbacks": [VerboseCallback()]}
    )
    print("\nKết quả cuối:")
    pprint(result.dict() if hasattr(result, "dict") else result)
    return result


def debug_collaborative():
    print("\n===[2/4] DEBUG COLLABORATIVE CHAIN===".center(80, "="))
    result = collaborative_chain.invoke(
        {"user_id": USER_ID}, config={"callbacks": [VerboseCallback()]}
    )
    print("\nKết quả cuối:")
    pprint(result.dict() if hasattr(result, "dict") else result)
    return result


def debug_trending():
    print("\n===[3/4] DEBUG TRENDING CHAIN (không cần user_id)===".center(80, "="))
    result = trending_chain.invoke({}, config={"callbacks": [VerboseCallback()]})
    print("\nKết quả cuối:")
    pprint(result.dict() if hasattr(result, "dict") else result)
    return result


def debug_master():
    print("\n===[4/4] DEBUG MASTER CHAIN===".center(80, "="))
    result = master_chain.invoke(
        {"user_id": USER_ID}, config={"callbacks": [VerboseCallback()]}
    )
    print("\nKết quả cuối – MENU HOÀN CHỈNH:")
    pprint(result)
    return result


# CALLBACK IN RA MỌI BƯỚC (SIÊU PHẨM)
from langchain_core.callbacks import BaseCallbackHandler


class VerboseCallback(BaseCallbackHandler):
    def on_chain_start(self, serialized, inputs, **kwargs):
        name = serialized.get("name", "Unknown")
        print(f"\n→ Bắt đầu: {name}")
        if "user_id" in inputs:
            print(f"   Input user_id: {inputs['user_id']}")
        if len(inputs) <= 5:
            print(f"   Inputs: {json.dumps(inputs, ensure_ascii=False, indent=2)}")

    def on_tool_start(self, serialized, input_str, **kwargs):
        print(f"   Tool gọi: {serialized.get('name')} | Input: {input_str[:200]}...")

    def on_llm_start(self, serialized, prompts, **kwargs):
        print(
            f"   LLM gọi: {serialized.get('name')} | Prompt length: {len(prompts[0])} ký tự"
        )

    def on_chain_end(self, outputs, **kwargs):
        if isinstance(outputs, dict) and len(outputs) <= 10:
            print(f"   Output: {json.dumps(outputs, ensure_ascii=False, indent=2)}")
        else:
            print(f"   Output: {type(outputs)} với {len(str(outputs))} ký tự")


# ")


# CHẠY TỪNG BƯỚC
if __name__ == "__main__":
    print("BẮT ĐẦU DEBUG TOÀN BỘ HỆ THỐNG".center(80, "#"))
    debug_behavioral()
    # debug_collaborative()
    # debug_trending()
    # debug_master()
