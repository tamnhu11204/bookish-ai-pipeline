from app.chains.collaborative_chain import collaborative_chain

print("🚀 BẮT ĐẦU TEST FULL COLLABORATIVE CHAIN\n")

result = collaborative_chain.invoke({
    "user_id": "6868164751471f57737434d5"
})

print("\n✅ KẾT QUẢ TRẢ VỀ TỪ CHAIN:\n")
print(result)

print("\n📌 KIỂM TRA CẤU TRÚC OUTPUT:\n")

# ✅ CÁCH ĐÚNG
if hasattr(result, "combos"):
    print("✅ Có field combos")
    print("👉 Số combo:", len(result.combos))
    for i, combo in enumerate(result.combos, 1):
        print(f"\nCombo {i}:")
        print("Title:", combo.title)
        print("Books:", combo.book_ids)
else:
    print("❌ Không có field combos")
