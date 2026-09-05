# AgentEval-CustomerService 评测报告

- 生成时间：2026-09-05T14:34:01
- Agent 运行时：`heuristic`
- DeepEval 裁判：`heuristic`
- 用例数：10
- 用例通过：10/10
- 平均节点分：0.979
- 平均轨迹分：1.000

## 1. 指标总览

节点级评测针对意图、路由、RAG、回复、工具；轨迹级评测看整条路径是否完成任务、是否绕路。

| 指标 | 平均分 | 通过率 |
| --- | --- | --- |
| IntentAccuracy | 1.000 ██████████ | 100% |
| RoutingCorrectness | 1.000 ██████████ | 100% |
| ReplyRelevancy | 1.000 ██████████ | 100% |
| ReplyCompleteness | 1.000 ██████████ | 100% |
| ReplyPoliteness | 0.967 ██████████ | 100% |
| ToolCorrectness | 1.000 ██████████ | 100% |
| TaskCompletion | 1.000 ██████████ | 100% |
| StepEfficiency | 1.000 ██████████ | 100% |
| RAGQuality | 0.817 ████████░░ | 100% |

## 2. 用例一览

| ID | 意图 | 路由 | 路径 | 综合 | 结果 |
| --- | --- | --- | --- | --- | --- |
| tc_greeting | greeting / greeting | direct_reply / direct_reply | intent_preprocess → supervisor → reply_generate | 1.00 | PASS |
| tc_product_battery | product_inquiry / product_inquiry | rag_agent / rag_agent | intent_preprocess → supervisor → rag_retrieve → reply_generate | 0.98 | PASS |
| tc_order_status | order_status / order_status | tool_agent / tool_agent | intent_preprocess → supervisor → reply_generate → tools → reply_generate | 1.00 | PASS |
| tc_refund_policy | refund / refund | rag_agent / rag_agent | intent_preprocess → supervisor → rag_retrieve → reply_generate | 0.99 | PASS |
| tc_refund_with_order | refund / refund | rag_agent / rag_agent | intent_preprocess → supervisor → rag_retrieve → reply_generate → tools → reply_generate | 0.98 | PASS |
| tc_shipping_eta | shipping / shipping | rag_agent / rag_agent | intent_preprocess → supervisor → rag_retrieve → reply_generate | 0.98 | PASS |
| tc_account_password | account / account | rag_agent / rag_agent | intent_preprocess → supervisor → rag_retrieve → reply_generate | 0.98 | PASS |
| tc_complaint | complaint / complaint | tool_agent / tool_agent | intent_preprocess → supervisor → reply_generate → tools → reply_generate | 1.00 | PASS |
| tc_out_of_scope | out_of_scope / out_of_scope | direct_reply / direct_reply | intent_preprocess → supervisor → reply_generate | 0.96 | PASS |
| tc_watch_compat | product_inquiry / product_inquiry | rag_agent / rag_agent | intent_preprocess → supervisor → rag_retrieve → reply_generate | 0.98 | PASS |

## 3. 用例 `tc_greeting` — PASS

**用户**：你好，在吗？

**任务**：友好地问候用户并表示可以提供客服帮助。

**最终回复**：您好，我是星云数码客服助手。可以帮您查订单、退换货政策、商品规格或账号问题，请问需要什么帮助？

**实际路径**：`intent_preprocess → supervisor → reply_generate`

**期望路径**：`intent_preprocess → supervisor → reply_generate`

### 节点级 Component Scores

| 节点/指标 | 分数 | 结果 | 来源 | 理由 |
| --- | --- | --- | --- | --- |
| IntentAccuracy | 1.00 ██████████ | PASS | deterministic | 预测意图 `greeting` 与标注 `greeting` 一致。 |
| RoutingCorrectness | 1.00 ██████████ | PASS | deterministic | Supervisor 路由 `direct_reply` 与标注 `direct_reply` 一致（意图=greeting）。 |
| RAGQuality | 1.00 ██████████ | PASS | deterministic | 该用例不需要检索，且节点未检索，视为正确跳过。 |
| ReplyRelevancy | 1.00 ██████████ | PASS | deterministic | 回复是否覆盖用户问题：要点命中 ['问候', '可以帮忙'] / ['问候', '可以帮忙']。 |
| ReplyCompleteness | 1.00 ██████████ | PASS | deterministic | 完整性：命中 2/2 个要点 ['问候', '可以帮忙']，缺失 []。 |
| ReplyPoliteness | 1.00 ██████████ | PASS | deterministic | 礼貌度：命中客服礼貌用语 ['请', '您', '您好', '帮您', '可以']。 |
| ToolCorrectness | 1.00 ██████████ | PASS | deterministic | 无需工具，也未调用工具。 |

### 轨迹级 Trajectory Scores

| 指标 | 分数 | 结果 | 来源 | 理由 |
| --- | --- | --- | --- | --- |
| TaskCompletion | 1.00 ██████████ | PASS | deterministic | 任务：友好地问候用户并表示可以提供客服帮助。。意图正确，路由正确，要点覆盖 100%。路径=['intent_preprocess', 'supervisor', 'reply_generate']，工具=[]。 |
| StepEfficiency | 1.00 ██████████ | PASS | deterministic | 轨迹完全一致：['intent_preprocess', 'supervisor', 'reply_generate'] |

<details><summary>节点 Trace（调试）</summary>

```json
[
  {
    "node": "intent_preprocess",
    "input": {
      "user_query": "你好，在吗？"
    },
    "output": {
      "intent": "greeting",
      "intent_confidence": 0.8500000000000001,
      "cleaned_query": "你好，在吗？",
      "entities": {
        "order_id": null,
        "product": null
      }
    },
    "latency_ms": 0.03
  },
  {
    "node": "supervisor",
    "input": {
      "intent": "greeting",
      "entities": {
        "order_id": null,
        "product": null
      }
    },
    "output": {
      "supervisor_intent": "greeting",
      "route": "direct_reply",
      "route_reason": "根据意图 greeting 按路由表分发给 direct_reply"
    },
    "latency_ms": 0.01
  },
  {
    "node": "reply_generate",
    "input": {
      "query": "你好，在吗？",
      "tool_round": 0
    },
    "output": {
      "action": "final_reply",
      "final_reply": "您好，我是星云数码客服助手。可以帮您查订单、退换货政策、商品规格或账号问题，请问需要什么帮助？"
    },
    "latency_ms": 0.02
  }
]
```

</details>

## 3. 用例 `tc_product_battery` — PASS

**用户**：星云降噪耳机 Pro 开降噪能用多久？包装里有没有音频线？

**任务**：根据知识库准确回答耳机续航和配件问题。

**最终回复**：您好，根据商品说明：开启降噪后续航约 28 小时，关闭降噪约 40 小时。包装内含 Type-C 充电线、3.5mm 音频线和收纳盒。 您可以继续问我其他规格。

**实际路径**：`intent_preprocess → supervisor → rag_retrieve → reply_generate`

**期望路径**：`intent_preprocess → supervisor → rag_retrieve → reply_generate`

### 节点级 Component Scores

| 节点/指标 | 分数 | 结果 | 来源 | 理由 |
| --- | --- | --- | --- | --- |
| IntentAccuracy | 1.00 ██████████ | PASS | deterministic | 预测意图 `product_inquiry` 与标注 `product_inquiry` 一致。 |
| RoutingCorrectness | 1.00 ██████████ | PASS | deterministic | Supervisor 路由 `rag_agent` 与标注 `rag_agent` 一致（意图=product_inquiry）。 |
| RAGQuality | 0.80 ████████░░ | PASS | deterministic | 检索命中 ['kb_wh100_specs']。召回=1.00 精确=0.33 F1=0.50 综合=0.80。 多余: kb_watch_s2,kb_warranty |
| ReplyRelevancy | 1.00 ██████████ | PASS | deterministic | 回复是否覆盖用户问题：要点命中 ['28小时', '3.5mm', '音频线'] / ['28小时', '3.5mm', '音频线']。 |
| ReplyCompleteness | 1.00 ██████████ | PASS | deterministic | 完整性：命中 3/3 个要点 ['28小时', '3.5mm', '音频线']，缺失 []。 |
| ReplyPoliteness | 1.00 ██████████ | PASS | deterministic | 礼貌度：命中客服礼貌用语 ['您', '您好', '可以']。 |
| ToolCorrectness | 1.00 ██████████ | PASS | deterministic | 无需工具，也未调用工具。 |

### 轨迹级 Trajectory Scores

| 指标 | 分数 | 结果 | 来源 | 理由 |
| --- | --- | --- | --- | --- |
| TaskCompletion | 1.00 ██████████ | PASS | deterministic | 任务：根据知识库准确回答耳机续航和配件问题。。意图正确，路由正确，要点覆盖 100%。路径=['intent_preprocess', 'supervisor', 'rag_retrieve', 'reply_generate']，工具=[]。 |
| StepEfficiency | 1.00 ██████████ | PASS | deterministic | 轨迹完全一致：['intent_preprocess', 'supervisor', 'rag_retrieve', 'reply_generate'] |

<details><summary>节点 Trace（调试）</summary>

```json
[
  {
    "node": "intent_preprocess",
    "input": {
      "user_query": "星云降噪耳机 Pro 开降噪能用多久？包装里有没有音频线？"
    },
    "output": {
      "intent": "product_inquiry",
      "intent_confidence": 0.95,
      "cleaned_query": "星云降噪耳机 Pro 开降噪能用多久？包装里有没有音频线？",
      "entities": {
        "order_id": null,
        "product": "星云降噪耳机 Pro"
      }
    },
    "latency_ms": 0.03
  },
  {
    "node": "supervisor",
    "input": {
      "intent": "product_inquiry",
      "entities": {
        "order_id": null,
        "product": "星云降噪耳机 Pro"
      }
    },
    "output": {
      "supervisor_intent": "product_inquiry",
      "route": "rag_agent",
      "route_reason": "根据意图 product_inquiry 按路由表分发给 rag_agent"
    },
    "latency_ms": 0.01
  },
  {
    "node": "rag_retrieve",
    "input": {
      "retrieval_query": "星云降噪耳机 Pro 开降噪能用多久？包装里有没有音频线？"
    },
    "output": {
      "retrieved_doc_ids": [
        "kb_wh100_specs",
        "kb_watch_s2",
        "kb_warranty"
      ],
      "titles": [
        "星云降噪耳机 Pro（WH-100）规格",
        "星云手表 S2 规格与兼容性",
        "全国联保与质保期限"
      ]
    },
    "latency_ms": 1.35
  },
  {
    "node": "reply_generate",
    "input": {
      "query": "星云降噪耳机 Pro 开降噪能用多久？包装里有没有音频线？",
      "tool_round": 0
    },
    "output": {
      "action": "final_reply",
      "final_reply": "您好，根据商品说明：开启降噪后续航约 28 小时，关闭降噪约 40 小时。包装内含 Type-C 充电线、3.5mm 音频线和收纳盒。 您可以继续问我其他规格。"
    },
    "latency_ms": 0.02
  }
]
```

</details>

## 3. 用例 `tc_order_status` — PASS

**用户**：帮我查一下订单 A20240901 发到哪了？

**任务**：调用订单和物流工具，向用户同步真实履约状态。

**最终回复**：您好，已为您查到：lookup_order: {"ok": true, "order_id": "A20240901", "status": "已发货", "product": "星云降噪耳机 Pro", "sku": "WH-100", "amount": 899.0, "paid_at": "2026-09-03 10:12", "shipped_at": "2026-09-03 18:40", "signed_at": null}
get_shipping_status: {"ok": true, "order_id": "A20240901", "status": "已发货", "carrier": "顺丰", "tracking_no": "SF1092388123", "eta": "2026-09-06", "last_event": "快件已到达【成都转运中心】"} 如需继续处理退换货或加急，请告诉我。

**实际路径**：`intent_preprocess → supervisor → reply_generate → tools → reply_generate`

**期望路径**：`intent_preprocess → supervisor → reply_generate → tools → reply_generate`

### 节点级 Component Scores

| 节点/指标 | 分数 | 结果 | 来源 | 理由 |
| --- | --- | --- | --- | --- |
| IntentAccuracy | 1.00 ██████████ | PASS | deterministic | 预测意图 `order_status` 与标注 `order_status` 一致。 |
| RoutingCorrectness | 1.00 ██████████ | PASS | deterministic | Supervisor 路由 `tool_agent` 与标注 `tool_agent` 一致（意图=order_status）。 |
| RAGQuality | 1.00 ██████████ | PASS | deterministic | 该用例不需要检索，且节点未检索，视为正确跳过。 |
| ReplyRelevancy | 1.00 ██████████ | PASS | deterministic | 回复是否覆盖用户问题：要点命中 ['已发货', '顺丰', 'SF'] / ['已发货', '顺丰', 'SF']。 |
| ReplyCompleteness | 1.00 ██████████ | PASS | deterministic | 完整性：命中 3/3 个要点 ['已发货', '顺丰', 'SF']，缺失 []。 |
| ReplyPoliteness | 1.00 ██████████ | PASS | deterministic | 礼貌度：命中客服礼貌用语 ['请', '您', '您好']。 |
| ToolCorrectness | 1.00 ██████████ | PASS | deterministic | 期望 ['lookup_order', 'get_shipping_status']，实际 ['lookup_order', 'get_shipping_status']。命中 ['lookup_order', 'get_shipping_status']，缺失 []，多余 []。 |

### 轨迹级 Trajectory Scores

| 指标 | 分数 | 结果 | 来源 | 理由 |
| --- | --- | --- | --- | --- |
| TaskCompletion | 1.00 ██████████ | PASS | deterministic | 任务：调用订单和物流工具，向用户同步真实履约状态。。意图正确，路由正确，要点覆盖 100%。路径=['intent_preprocess', 'supervisor', 'reply_generate', 'tools', 'reply_generate']，工具=['lookup_order', 'get_shipping_status']。 |
| StepEfficiency | 1.00 ██████████ | PASS | deterministic | 轨迹完全一致：['intent_preprocess', 'supervisor', 'reply_generate', 'tools', 'reply_generate'] |

<details><summary>节点 Trace（调试）</summary>

```json
[
  {
    "node": "intent_preprocess",
    "input": {
      "user_query": "帮我查一下订单 A20240901 发到哪了？"
    },
    "output": {
      "intent": "order_status",
      "intent_confidence": 0.95,
      "cleaned_query": "帮我查一下订单 A20240901 发到哪了？",
      "entities": {
        "order_id": "A20240901",
        "product": null
      }
    },
    "latency_ms": 0.02
  },
  {
    "node": "supervisor",
    "input": {
      "intent": "order_status",
      "entities": {
        "order_id": "A20240901",
        "product": null
      }
    },
    "output": {
      "supervisor_intent": "order_status",
      "route": "tool_agent",
      "route_reason": "根据意图 order_status 按路由表分发给 tool_agent"
    },
    "latency_ms": 0.01
  },
  {
    "node": "reply_generate",
    "input": {
      "query": "帮我查一下订单 A20240901 发到哪了？",
      "tool_round": 0
    },
    "output": {
      "action": "call_tools",
      "tool_calls": [
        {
          "name": "lookup_order",
          "args": {
            "order_id": "A20240901"
          },
          "id": "call_lookup_order_45558208",
          "type": "tool_call"
        },
        {
          "name": "get_shipping_status",
          "args": {
            "order_id": "A20240901"
          },
          "id": "call_get_shipping_status_8feec152",
          "type": "tool_call"
        }
      ],
      "tool_round": 0
    },
    "latency_ms": 0.12
  },
  {
    "node": "tools",
    "input": {
      "tool_round": 0
    },
    "output": {
      "tools_called": [
        {
          "name": "lookup_order",
          "args": {
            "order_id": "A20240901"
          },
          "output": "{\"ok\": true, \"order_id\": \"A20240901\", \"status\": \"已发货\", \"product\": \"星云降噪耳机 Pro\", \"sku\": \"WH-100\", \"amount\": 899.0, \"paid_at\": \"2026-09-03 10:12\", \"shipped_at\": \"2026-09-03 18:40\", \"signed_at\": null}"
        },
        {
          "name": "get_shipping_status",
          "args": {
            "order_id": "A20240901"
          },
          "output": "{\"ok\": true, \"order_id\": \"A20240901\", \"status\": \"已发货\", \"carrier\": \"顺丰\", \"tracking_no\": \"SF1092388123\", \"eta\": \"2026-09-06\", \"last_event\": \"快件已到达【成都转运中心】\"}"
        }
      ]
    },
    "latency_ms": 1.02
  },
  {
    "node": "reply_generate",
    "input": {
      "query": "帮我查一下订单 A20240901 发到哪了？",
      "tool_round": 1
    },
    "output": {
      "action": "final_reply",
      "final_reply": "您好，已为您查到：lookup_order: {\"ok\": true, \"order_id\": \"A20240901\", \"status\": \"已发货\", \"product\": \"星云降噪耳机 Pro\", \"sku\": \"WH-100\", \"amount\": 899.0, \"paid_at\": \"2026-09-03 10:12\", \"shipped_at\": \"2026-09-03 18:40\", \"signed_at\": null}\nget_shipping_status: {\"ok\": true, \"order_id\": \"A20240901\", \"status\": \"已发货\", \"carrier\": \"顺丰\", \"tracking_no\": \"SF1092388123\", \"eta\": \"2026-09-06\", \"last_event\": \"快件已到达【成都转运中心】\"} 如需继续处理退换货或加急，请告诉我。"
    },
    "latency_ms": 0.02
  }
]
```

</details>

## 3. 用例 `tc_refund_policy` — PASS

**用户**：签收几天内可以无理由退货？退款大概多久到账？

**任务**：检索退货退款政策并完整回答时限与到账时间。

**最终回复**：您好，星云数码支持签收后7天内无理由退货。商品需保持原包装完整、配件齐全、无人为损坏。已激活的软件授权、定制刻字商品不在无理由退货范围内。申请入口：订单详情页 → 申请售后。审核通过后将生成上门取件或自寄运单。 退货商品入库质检通过后，退款将在1-3个工作日内原路返回。微信支付一般24小时内到账，银行卡可能需要1-3个工作日。若超过3个工作日未到账，请提供订单号由客服核查支付流水。 您可以按上述说明办理，需要我帮您操作请再说一声。

**实际路径**：`intent_preprocess → supervisor → rag_retrieve → reply_generate`

**期望路径**：`intent_preprocess → supervisor → rag_retrieve → reply_generate`

### 节点级 Component Scores

| 节点/指标 | 分数 | 结果 | 来源 | 理由 |
| --- | --- | --- | --- | --- |
| IntentAccuracy | 1.00 ██████████ | PASS | deterministic | 预测意图 `refund` 与标注 `refund` 一致。 |
| RoutingCorrectness | 1.00 ██████████ | PASS | deterministic | Supervisor 路由 `rag_agent` 与标注 `rag_agent` 一致（意图=refund）。 |
| RAGQuality | 0.90 █████████░ | PASS | deterministic | 检索命中 ['kb_refund_timeline', 'kb_return_7day']。召回=1.00 精确=0.67 F1=0.80 综合=0.90。 多余: kb_refund_quality |
| ReplyRelevancy | 1.00 ██████████ | PASS | deterministic | 回复是否覆盖用户问题：要点命中 ['7天', '1-3个工作日', '原路返回'] / ['7天', '1-3个工作日', '原路返回']。 |
| ReplyCompleteness | 1.00 ██████████ | PASS | deterministic | 完整性：命中 3/3 个要点 ['7天', '1-3个工作日', '原路返回']，缺失 []。 |
| ReplyPoliteness | 1.00 ██████████ | PASS | deterministic | 礼貌度：命中客服礼貌用语 ['请', '您', '您好', '帮您', '可以']。 |
| ToolCorrectness | 1.00 ██████████ | PASS | deterministic | 无需工具，也未调用工具。 |

### 轨迹级 Trajectory Scores

| 指标 | 分数 | 结果 | 来源 | 理由 |
| --- | --- | --- | --- | --- |
| TaskCompletion | 1.00 ██████████ | PASS | deterministic | 任务：检索退货退款政策并完整回答时限与到账时间。。意图正确，路由正确，要点覆盖 100%。路径=['intent_preprocess', 'supervisor', 'rag_retrieve', 'reply_generate']，工具=[]。 |
| StepEfficiency | 1.00 ██████████ | PASS | deterministic | 轨迹完全一致：['intent_preprocess', 'supervisor', 'rag_retrieve', 'reply_generate'] |

<details><summary>节点 Trace（调试）</summary>

```json
[
  {
    "node": "intent_preprocess",
    "input": {
      "user_query": "签收几天内可以无理由退货？退款大概多久到账？"
    },
    "output": {
      "intent": "refund",
      "intent_confidence": 0.95,
      "cleaned_query": "签收几天内可以无理由退货？退款大概多久到账？",
      "entities": {
        "order_id": null,
        "product": null
      }
    },
    "latency_ms": 0.02
  },
  {
    "node": "supervisor",
    "input": {
      "intent": "refund",
      "entities": {
        "order_id": null,
        "product": null
      }
    },
    "output": {
      "supervisor_intent": "refund",
      "route": "rag_agent",
      "route_reason": "根据意图 refund 按路由表分发给 rag_agent"
    },
    "latency_ms": 0.01
  },
  {
    "node": "rag_retrieve",
    "input": {
      "retrieval_query": "签收几天内可以无理由退货？退款大概多久到账？"
    },
    "output": {
      "retrieved_doc_ids": [
        "kb_return_7day",
        "kb_refund_timeline",
        "kb_refund_quality"
      ],
      "titles": [
        "7天无理由退货政策",
        "退款到账时间",
        "质量问题退换货"
      ]
    },
    "latency_ms": 0.44
  },
  {
    "node": "reply_generate",
    "input": {
      "query": "签收几天内可以无理由退货？退款大概多久到账？",
      "tool_round": 0
    },
    "output": {
      "action": "final_reply",
      "final_reply": "您好，星云数码支持签收后7天内无理由退货。商品需保持原包装完整、配件齐全、无人为损坏。已激活的软件授权、定制刻字商品不在无理由退货范围内。申请入口：订单详情页 → 申请售后。审核通过后将生成上门取件或自寄运单。 退货商品入库质检通过后，退款将在1-3个工作日内原路返回。微信支付一般24小时内到账，银行卡可能需要1-3个工作日。若超过3个工作日未到账，请提供订单号由客服核查支付流水。 您可以按上述说明办理，需要我帮您操作请再说一声。"
    },
    "latency_ms": 0.01
  }
]
```

</details>

## 3. 用例 `tc_refund_with_order` — PASS

**用户**：我订单 A20240888 想退货，还能退吗？能退多少钱？

**任务**：先检索退货政策，再调用订单/退款工具给出是否可退和金额。

**最终回复**：您好，星云数码支持签收后7天内无理由退货。商品需保持原包装完整、配件齐全、无人为损坏。已激活的软件授权、定制刻字商品不在无理由退货范围内。申请入口：订单详情页 → 申请售后。审核通过后将生成上门取件或自寄运单。 因质量问题或物流损坏导致的退换货，不受7天无理由时限限制，在质保期内均可申请。请提供开箱视频或清晰照片。质量问题退货的往返运费由星云数码承担，通常会安排上门取件。 结合您的订单数据：lookup_order: {"ok": true, "order_id": "A20240888", "status": "已签收", "product": "星云降噪耳机 Pro", "sku": "WH-100", "amount": 899.0, "paid_at": "2026-08-28 09:01", "shipped_at": "2026-08-28 16:20", "signed_at": "2026-08-31 14:08"}
calculate_refund: {"ok": true, "order_id": "A20240888", "reason": "无理由退货", "refundable": true, "refund_amount": 899.0, "hint": "签收未满7天，可走无理由退货。"} 您可以按上述说明办理，需要我帮您操作请再说一声。

**实际路径**：`intent_preprocess → supervisor → rag_retrieve → reply_generate → tools → reply_generate`

**期望路径**：`intent_preprocess → supervisor → rag_retrieve → reply_generate → tools → reply_generate`

### 节点级 Component Scores

| 节点/指标 | 分数 | 结果 | 来源 | 理由 |
| --- | --- | --- | --- | --- |
| IntentAccuracy | 1.00 ██████████ | PASS | deterministic | 预测意图 `refund` 与标注 `refund` 一致。 |
| RoutingCorrectness | 1.00 ██████████ | PASS | deterministic | Supervisor 路由 `rag_agent` 与标注 `rag_agent` 一致（意图=refund）。 |
| RAGQuality | 0.80 ████████░░ | PASS | deterministic | 检索命中 ['kb_return_7day']。召回=1.00 精确=0.33 F1=0.50 综合=0.80。 多余: kb_refund_quality,kb_refund_timeline |
| ReplyRelevancy | 1.00 ██████████ | PASS | deterministic | 回复是否覆盖用户问题：要点命中 ['7天', '已签收', '899'] / ['7天', '已签收', '899']。 |
| ReplyCompleteness | 1.00 ██████████ | PASS | deterministic | 完整性：命中 3/3 个要点 ['7天', '已签收', '899']，缺失 []。 |
| ReplyPoliteness | 1.00 ██████████ | PASS | deterministic | 礼貌度：命中客服礼貌用语 ['请', '您', '您好', '帮您', '可以']。 |
| ToolCorrectness | 1.00 ██████████ | PASS | deterministic | 期望 ['lookup_order', 'calculate_refund']，实际 ['lookup_order', 'calculate_refund']。命中 ['lookup_order', 'calculate_refund']，缺失 []，多余 []。 |

### 轨迹级 Trajectory Scores

| 指标 | 分数 | 结果 | 来源 | 理由 |
| --- | --- | --- | --- | --- |
| TaskCompletion | 1.00 ██████████ | PASS | deterministic | 任务：先检索退货政策，再调用订单/退款工具给出是否可退和金额。。意图正确，路由正确，要点覆盖 100%。路径=['intent_preprocess', 'supervisor', 'rag_retrieve', 'reply_generate', 'tools', 'reply_generate']，工具=['lookup_order', 'calculate_refund']。 |
| StepEfficiency | 1.00 ██████████ | PASS | deterministic | 轨迹完全一致：['intent_preprocess', 'supervisor', 'rag_retrieve', 'reply_generate', 'tools', 'reply_generate'] |

<details><summary>节点 Trace（调试）</summary>

```json
[
  {
    "node": "intent_preprocess",
    "input": {
      "user_query": "我订单 A20240888 想退货，还能退吗？能退多少钱？"
    },
    "output": {
      "intent": "refund",
      "intent_confidence": 0.95,
      "cleaned_query": "我订单 A20240888 想退货，还能退吗？能退多少钱？",
      "entities": {
        "order_id": "A20240888",
        "product": null
      }
    },
    "latency_ms": 0.02
  },
  {
    "node": "supervisor",
    "input": {
      "intent": "refund",
      "entities": {
        "order_id": "A20240888",
        "product": null
      }
    },
    "output": {
      "supervisor_intent": "refund",
      "route": "rag_agent",
      "route_reason": "根据意图 refund 按路由表分发给 rag_agent"
    },
    "latency_ms": 0.0
  },
  {
    "node": "rag_retrieve",
    "input": {
      "retrieval_query": "我订单 A20240888 想退货，还能退吗？能退多少钱？"
    },
    "output": {
      "retrieved_doc_ids": [
        "kb_return_7day",
        "kb_refund_quality",
        "kb_refund_timeline"
      ],
      "titles": [
        "7天无理由退货政策",
        "质量问题退换货",
        "退款到账时间"
      ]
    },
    "latency_ms": 0.7
  },
  {
    "node": "reply_generate",
    "input": {
      "query": "我订单 A20240888 想退货，还能退吗？能退多少钱？",
      "tool_round": 0
    },
    "output": {
      "action": "call_tools",
      "tool_calls": [
        {
          "name": "lookup_order",
          "args": {
            "order_id": "A20240888"
          },
          "id": "call_lookup_order_45fad73d",
          "type": "tool_call"
        },
        {
          "name": "calculate_refund",
          "args": {
            "order_id": "A20240888",
            "reason": "无理由退货"
          },
          "id": "call_calculate_refund_5ce48b84",
          "type": "tool_call"
        }
      ],
      "tool_round": 0
    },
    "latency_ms": 0.03
  },
  {
    "node": "tools",
    "input": {
      "tool_round": 0
    },
    "output": {
      "tools_called": [
        {
          "name": "lookup_order",
          "args": {
            "order_id": "A20240888"
          },
          "output": "{\"ok\": true, \"order_id\": \"A20240888\", \"status\": \"已签收\", \"product\": \"星云降噪耳机 Pro\", \"sku\": \"WH-100\", \"amount\": 899.0, \"paid_at\": \"2026-08-28 09:01\", \"shipped_at\": \"2026-08-28 16:20\", \"signed_at\": \"2026-08-31 14:08\"}"
        },
        {
          "name": "calculate_refund",
          "args": {
            "order_id": "A20240888",
            "reason": "无理由退货"
          },
          "output": "{\"ok\": true, \"order_id\": \"A20240888\", \"reason\": \"无理由退货\", \"refundable\": true, \"refund_amount\": 899.0, \"hint\": \"签收未满7天，可走无理由退货。\"}"
        }
      ]
    },
    "latency_ms": 0.71
  },
  {
    "node": "reply_generate",
    "input": {
      "query": "我订单 A20240888 想退货，还能退吗？能退多少钱？",
      "tool_round": 1
    },
    "output": {
      "action": "final_reply",
      "final_reply": "您好，星云数码支持签收后7天内无理由退货。商品需保持原包装完整、配件齐全、无人为损坏。已激活的软件授权、定制刻字商品不在无理由退货范围内。申请入口：订单详情页 → 申请售后。审核通过后将生成上门取件或自寄运单。 因质量问题或物流损坏导致的退换货，不受7天无理由时限限制，在质保期内均可申请。请提供开箱视频或清晰照片。质量问题退货的往返运费由星云数码承担，通常会安排上门取件。 结合您的订单数据：lookup_order: {\"ok\": true, \"order_id\": \"A20240888\", \"status\": \"已签收\", \"product\": \"星云降噪耳机 Pro\", \"sku\": \"WH-100\", \"amount\": 899.0, \"paid_at\": \"2026-08-28 09:01\", \"shipped_at\": \"2026-08-28 16:20\", \"signed_at\": \"2026-08-31 14:08\"}\ncalculate_refund: {\"ok\": true, \"order_id\": \"A20240888\", \"reason\": \"无理由退货\", \"refundable\": true, \"refund_amount\": 899.0, \"hint\": \"签收未满7天，可走无理由退货。\"} 您可以按上述说明办理，需要我帮您操作请再说一声。"
    },
    "latency_ms": 0.02
  }
]
```

</details>

## 3. 用例 `tc_shipping_eta` — PASS

**用户**：现货下单的话发货要多久？我在成都大概几天能收到？

**任务**：检索配送时效知识，回答发货时间和成都预计送达天数。

**最终回复**：您好，现货订单在付款后24小时内发出（周末及法定节假日顺延）。江浙沪皖一般2-3天送达，其他省份3-5天，偏远地区5-8天。预售商品以商品页标注的发货时间为准。可在订单详情查看物流单号。 订单处于「待发货」时可自行修改收货地址。一旦进入「已发货」，需联系客服尝试拦截，成功与否取决于物流商进度，无法保证。拦截失败时建议收货后再申请退货或转寄。 您可以按上述说明办理，需要我帮您操作请再说一声。

**实际路径**：`intent_preprocess → supervisor → rag_retrieve → reply_generate`

**期望路径**：`intent_preprocess → supervisor → rag_retrieve → reply_generate`

### 节点级 Component Scores

| 节点/指标 | 分数 | 结果 | 来源 | 理由 |
| --- | --- | --- | --- | --- |
| IntentAccuracy | 1.00 ██████████ | PASS | deterministic | 预测意图 `shipping` 与标注 `shipping` 一致。 |
| RoutingCorrectness | 1.00 ██████████ | PASS | deterministic | Supervisor 路由 `rag_agent` 与标注 `rag_agent` 一致（意图=shipping）。 |
| RAGQuality | 0.80 ████████░░ | PASS | deterministic | 检索命中 ['kb_shipping_time']。召回=1.00 精确=0.33 F1=0.50 综合=0.80。 多余: kb_shipping_change,kb_membership |
| ReplyRelevancy | 1.00 ██████████ | PASS | deterministic | 回复是否覆盖用户问题：要点命中 ['24小时', '3-5天'] / ['24小时', '3-5天']。 |
| ReplyCompleteness | 1.00 ██████████ | PASS | deterministic | 完整性：命中 2/2 个要点 ['24小时', '3-5天']，缺失 []。 |
| ReplyPoliteness | 1.00 ██████████ | PASS | deterministic | 礼貌度：命中客服礼貌用语 ['请', '您', '您好', '帮您', '可以']。 |
| ToolCorrectness | 1.00 ██████████ | PASS | deterministic | 无需工具，也未调用工具。 |

### 轨迹级 Trajectory Scores

| 指标 | 分数 | 结果 | 来源 | 理由 |
| --- | --- | --- | --- | --- |
| TaskCompletion | 1.00 ██████████ | PASS | deterministic | 任务：检索配送时效知识，回答发货时间和成都预计送达天数。。意图正确，路由正确，要点覆盖 100%。路径=['intent_preprocess', 'supervisor', 'rag_retrieve', 'reply_generate']，工具=[]。 |
| StepEfficiency | 1.00 ██████████ | PASS | deterministic | 轨迹完全一致：['intent_preprocess', 'supervisor', 'rag_retrieve', 'reply_generate'] |

<details><summary>节点 Trace（调试）</summary>

```json
[
  {
    "node": "intent_preprocess",
    "input": {
      "user_query": "现货下单的话发货要多久？我在成都大概几天能收到？"
    },
    "output": {
      "intent": "shipping",
      "intent_confidence": 0.8500000000000001,
      "cleaned_query": "现货下单的话发货要多久？我在成都大概几天能收到？",
      "entities": {
        "order_id": null,
        "product": null
      }
    },
    "latency_ms": 0.02
  },
  {
    "node": "supervisor",
    "input": {
      "intent": "shipping",
      "entities": {
        "order_id": null,
        "product": null
      }
    },
    "output": {
      "supervisor_intent": "shipping",
      "route": "rag_agent",
      "route_reason": "根据意图 shipping 按路由表分发给 rag_agent"
    },
    "latency_ms": 0.0
  },
  {
    "node": "rag_retrieve",
    "input": {
      "retrieval_query": "现货下单的话发货要多久？我在成都大概几天能收到？"
    },
    "output": {
      "retrieved_doc_ids": [
        "kb_shipping_time",
        "kb_shipping_change",
        "kb_membership"
      ],
      "titles": [
        "发货与配送时效",
        "修改地址与拦截包裹",
        "星云会员积分规则"
      ]
    },
    "latency_ms": 0.44
  },
  {
    "node": "reply_generate",
    "input": {
      "query": "现货下单的话发货要多久？我在成都大概几天能收到？",
      "tool_round": 0
    },
    "output": {
      "action": "final_reply",
      "final_reply": "您好，现货订单在付款后24小时内发出（周末及法定节假日顺延）。江浙沪皖一般2-3天送达，其他省份3-5天，偏远地区5-8天。预售商品以商品页标注的发货时间为准。可在订单详情查看物流单号。 订单处于「待发货」时可自行修改收货地址。一旦进入「已发货」，需联系客服尝试拦截，成功与否取决于物流商进度，无法保证。拦截失败时建议收货后再申请退货或转寄。 您可以按上述说明办理，需要我帮您操作请再说一声。"
    },
    "latency_ms": 0.01
  }
]
```

</details>

## 3. 用例 `tc_account_password` — PASS

**用户**：我换手机号了，登录密码忘了，怎么找回？

**任务**：根据账号帮助文档指导用户找回密码。

**最终回复**：您好，在登录页点击「忘记密码」，通过绑定手机号或邮箱接收验证码即可重置。若手机号已停用，请提供订单号、注册邮箱与最近一次收货人信息，由人工核验后解绑。请勿向客服以外的人员泄露验证码。 发现异常登录请立即修改密码并开启二次验证。账号注销需在「设置 → 隐私 → 注销账号」提交，有未完成订单或售后单时无法注销。注销后个人数据将在 15 个工作日内删除，无法恢复积分与优惠券。 您可以按上述说明办理，需要我帮您操作请再说一声。

**实际路径**：`intent_preprocess → supervisor → rag_retrieve → reply_generate`

**期望路径**：`intent_preprocess → supervisor → rag_retrieve → reply_generate`

### 节点级 Component Scores

| 节点/指标 | 分数 | 结果 | 来源 | 理由 |
| --- | --- | --- | --- | --- |
| IntentAccuracy | 1.00 ██████████ | PASS | deterministic | 预测意图 `account` 与标注 `account` 一致。 |
| RoutingCorrectness | 1.00 ██████████ | PASS | deterministic | Supervisor 路由 `rag_agent` 与标注 `rag_agent` 一致（意图=account）。 |
| RAGQuality | 0.80 ████████░░ | PASS | deterministic | 检索命中 ['kb_account_password']。召回=1.00 精确=0.33 F1=0.50 综合=0.80。 多余: kb_account_privacy,kb_invoice |
| ReplyRelevancy | 1.00 ██████████ | PASS | deterministic | 回复是否覆盖用户问题：要点命中 ['忘记密码', '人工核验', '订单号'] / ['忘记密码', '人工核验', '订单号']。 |
| ReplyCompleteness | 1.00 ██████████ | PASS | deterministic | 完整性：命中 3/3 个要点 ['忘记密码', '人工核验', '订单号']，缺失 []。 |
| ReplyPoliteness | 1.00 ██████████ | PASS | deterministic | 礼貌度：命中客服礼貌用语 ['请', '您', '您好', '帮您', '可以']。 |
| ToolCorrectness | 1.00 ██████████ | PASS | deterministic | 无需工具，也未调用工具。 |

### 轨迹级 Trajectory Scores

| 指标 | 分数 | 结果 | 来源 | 理由 |
| --- | --- | --- | --- | --- |
| TaskCompletion | 1.00 ██████████ | PASS | deterministic | 任务：根据账号帮助文档指导用户找回密码。。意图正确，路由正确，要点覆盖 100%。路径=['intent_preprocess', 'supervisor', 'rag_retrieve', 'reply_generate']，工具=[]。 |
| StepEfficiency | 1.00 ██████████ | PASS | deterministic | 轨迹完全一致：['intent_preprocess', 'supervisor', 'rag_retrieve', 'reply_generate'] |

<details><summary>节点 Trace（调试）</summary>

```json
[
  {
    "node": "intent_preprocess",
    "input": {
      "user_query": "我换手机号了，登录密码忘了，怎么找回？"
    },
    "output": {
      "intent": "account",
      "intent_confidence": 0.8500000000000001,
      "cleaned_query": "我换手机号了，登录密码忘了，怎么找回？",
      "entities": {
        "order_id": null,
        "product": null
      }
    },
    "latency_ms": 0.01
  },
  {
    "node": "supervisor",
    "input": {
      "intent": "account",
      "entities": {
        "order_id": null,
        "product": null
      }
    },
    "output": {
      "supervisor_intent": "account",
      "route": "rag_agent",
      "route_reason": "根据意图 account 按路由表分发给 rag_agent"
    },
    "latency_ms": 0.01
  },
  {
    "node": "rag_retrieve",
    "input": {
      "retrieval_query": "我换手机号了，登录密码忘了，怎么找回？"
    },
    "output": {
      "retrieved_doc_ids": [
        "kb_account_password",
        "kb_account_privacy",
        "kb_invoice"
      ],
      "titles": [
        "账号与密码找回",
        "账号安全与注销",
        "发票开具说明"
      ]
    },
    "latency_ms": 0.44
  },
  {
    "node": "reply_generate",
    "input": {
      "query": "我换手机号了，登录密码忘了，怎么找回？",
      "tool_round": 0
    },
    "output": {
      "action": "final_reply",
      "final_reply": "您好，在登录页点击「忘记密码」，通过绑定手机号或邮箱接收验证码即可重置。若手机号已停用，请提供订单号、注册邮箱与最近一次收货人信息，由人工核验后解绑。请勿向客服以外的人员泄露验证码。 发现异常登录请立即修改密码并开启二次验证。账号注销需在「设置 → 隐私 → 注销账号」提交，有未完成订单或售后单时无法注销。注销后个人数据将在 15 个工作日内删除，无法恢复积分与优惠券。 您可以按上述说明办理，需要我帮您操作请再说一声。"
    },
    "latency_ms": 0.01
  }
]
```

</details>

## 3. 用例 `tc_complaint` — PASS

**用户**：物流把盒子都撞坏了，耳机外观有划痕，我要投诉！订单是 A20240901。

**任务**：安抚用户、查询订单并创建投诉工单。

**最终回复**：抱歉给您添麻烦了，已为您查询：lookup_order: {"ok": true, "order_id": "A20240901", "status": "已发货", "product": "星云降噪耳机 Pro", "sku": "WH-100", "amount": 899.0, "paid_at": "2026-09-03 10:12", "shipped_at": "2026-09-03 18:40", "signed_at": null}
create_ticket: {"ok": true, "ticket_id": "TK-0901-01", "category": "complaint", "order_id": "A20240901", "summary": "物流把盒子都撞坏了，耳机外观有划痕，我要投诉！订单是 A20240901。", "sla": "将在2小时内由人工客服回电或在线回复"} 如需继续处理退换货或加急，请告诉我。

**实际路径**：`intent_preprocess → supervisor → reply_generate → tools → reply_generate`

**期望路径**：`intent_preprocess → supervisor → reply_generate → tools → reply_generate`

### 节点级 Component Scores

| 节点/指标 | 分数 | 结果 | 来源 | 理由 |
| --- | --- | --- | --- | --- |
| IntentAccuracy | 1.00 ██████████ | PASS | deterministic | 预测意图 `complaint` 与标注 `complaint` 一致。 |
| RoutingCorrectness | 1.00 ██████████ | PASS | deterministic | Supervisor 路由 `tool_agent` 与标注 `tool_agent` 一致（意图=complaint）。 |
| RAGQuality | 1.00 ██████████ | PASS | deterministic | 该用例不需要检索，且节点未检索，视为正确跳过。 |
| ReplyRelevancy | 1.00 ██████████ | PASS | deterministic | 回复是否覆盖用户问题：要点命中 ['抱歉', '工单', '质量'] / ['抱歉', '工单', '质量']。 |
| ReplyCompleteness | 1.00 ██████████ | PASS | deterministic | 完整性：命中 3/3 个要点 ['抱歉', '工单', '质量']，缺失 []。 |
| ReplyPoliteness | 1.00 ██████████ | PASS | deterministic | 礼貌度：命中客服礼貌用语 ['请', '您', '抱歉']。 |
| ToolCorrectness | 1.00 ██████████ | PASS | deterministic | 期望 ['lookup_order', 'create_ticket']，实际 ['lookup_order', 'create_ticket']。命中 ['lookup_order', 'create_ticket']，缺失 []，多余 []。 |

### 轨迹级 Trajectory Scores

| 指标 | 分数 | 结果 | 来源 | 理由 |
| --- | --- | --- | --- | --- |
| TaskCompletion | 1.00 ██████████ | PASS | deterministic | 任务：安抚用户、查询订单并创建投诉工单。。意图正确，路由正确，要点覆盖 100%。路径=['intent_preprocess', 'supervisor', 'reply_generate', 'tools', 'reply_generate']，工具=['lookup_order', 'create_ticket']。 |
| StepEfficiency | 1.00 ██████████ | PASS | deterministic | 轨迹完全一致：['intent_preprocess', 'supervisor', 'reply_generate', 'tools', 'reply_generate'] |

<details><summary>节点 Trace（调试）</summary>

```json
[
  {
    "node": "intent_preprocess",
    "input": {
      "user_query": "物流把盒子都撞坏了，耳机外观有划痕，我要投诉！订单是 A20240901。"
    },
    "output": {
      "intent": "complaint",
      "intent_confidence": 0.95,
      "cleaned_query": "物流把盒子都撞坏了，耳机外观有划痕，我要投诉！订单是 A20240901。",
      "entities": {
        "order_id": "A20240901",
        "product": "星云降噪耳机 Pro"
      }
    },
    "latency_ms": 0.02
  },
  {
    "node": "supervisor",
    "input": {
      "intent": "complaint",
      "entities": {
        "order_id": "A20240901",
        "product": "星云降噪耳机 Pro"
      }
    },
    "output": {
      "supervisor_intent": "complaint",
      "route": "tool_agent",
      "route_reason": "根据意图 complaint 按路由表分发给 tool_agent"
    },
    "latency_ms": 0.0
  },
  {
    "node": "reply_generate",
    "input": {
      "query": "物流把盒子都撞坏了，耳机外观有划痕，我要投诉！订单是 A20240901。",
      "tool_round": 0
    },
    "output": {
      "action": "call_tools",
      "tool_calls": [
        {
          "name": "lookup_order",
          "args": {
            "order_id": "A20240901"
          },
          "id": "call_lookup_order_cdf5cfc0",
          "type": "tool_call"
        },
        {
          "name": "create_ticket",
          "args": {
            "category": "complaint",
            "summary": "物流把盒子都撞坏了，耳机外观有划痕，我要投诉！订单是 A20240901。",
            "order_id": "A20240901"
          },
          "id": "call_create_ticket_f657a90e",
          "type": "tool_call"
        }
      ],
      "tool_round": 0
    },
    "latency_ms": 0.02
  },
  {
    "node": "tools",
    "input": {
      "tool_round": 0
    },
    "output": {
      "tools_called": [
        {
          "name": "lookup_order",
          "args": {
            "order_id": "A20240901"
          },
          "output": "{\"ok\": true, \"order_id\": \"A20240901\", \"status\": \"已发货\", \"product\": \"星云降噪耳机 Pro\", \"sku\": \"WH-100\", \"amount\": 899.0, \"paid_at\": \"2026-09-03 10:12\", \"shipped_at\": \"2026-09-03 18:40\", \"signed_at\": null}"
        },
        {
          "name": "create_ticket",
          "args": {
            "category": "complaint",
            "summary": "物流把盒子都撞坏了，耳机外观有划痕，我要投诉！订单是 A20240901。",
            "order_id": "A20240901"
          },
          "output": "{\"ok\": true, \"ticket_id\": \"TK-0901-01\", \"category\": \"complaint\", \"order_id\": \"A20240901\", \"summary\": \"物流把盒子都撞坏了，耳机外观有划痕，我要投诉！订单是 A20240901。\", \"sla\": \"将在2小时内由人工客服回电或在线回复\"}"
        }
      ]
    },
    "latency_ms": 0.55
  },
  {
    "node": "reply_generate",
    "input": {
      "query": "物流把盒子都撞坏了，耳机外观有划痕，我要投诉！订单是 A20240901。",
      "tool_round": 1
    },
    "output": {
      "action": "final_reply",
      "final_reply": "抱歉给您添麻烦了，已为您查询：lookup_order: {\"ok\": true, \"order_id\": \"A20240901\", \"status\": \"已发货\", \"product\": \"星云降噪耳机 Pro\", \"sku\": \"WH-100\", \"amount\": 899.0, \"paid_at\": \"2026-09-03 10:12\", \"shipped_at\": \"2026-09-03 18:40\", \"signed_at\": null}\ncreate_ticket: {\"ok\": true, \"ticket_id\": \"TK-0901-01\", \"category\": \"complaint\", \"order_id\": \"A20240901\", \"summary\": \"物流把盒子都撞坏了，耳机外观有划痕，我要投诉！订单是 A20240901。\", \"sla\": \"将在2小时内由人工客服回电或在线回复\"} 如需继续处理退换货或加急，请告诉我。"
    },
    "latency_ms": 0.01
  }
]
```

</details>

## 3. 用例 `tc_out_of_scope` — PASS

**用户**：明天北京会下雨吗？顺便帮我写一首诗。

**任务**：识别超范围请求，拒绝天气/写诗并引导回客服场景。

**最终回复**：这个问题超出了我的职责范围，我这边主要处理购物、物流、退换货和账号售后。如果您有订单或商品相关的问题，我很乐意继续帮您。

**实际路径**：`intent_preprocess → supervisor → reply_generate`

**期望路径**：`intent_preprocess → supervisor → reply_generate`

### 节点级 Component Scores

| 节点/指标 | 分数 | 结果 | 来源 | 理由 |
| --- | --- | --- | --- | --- |
| IntentAccuracy | 1.00 ██████████ | PASS | deterministic | 预测意图 `out_of_scope` 与标注 `out_of_scope` 一致。 |
| RoutingCorrectness | 1.00 ██████████ | PASS | deterministic | Supervisor 路由 `direct_reply` 与标注 `direct_reply` 一致（意图=out_of_scope）。 |
| RAGQuality | 1.00 ██████████ | PASS | deterministic | 该用例不需要检索，且节点未检索，视为正确跳过。 |
| ReplyRelevancy | 1.00 ██████████ | PASS | deterministic | 回复是否覆盖用户问题：要点命中 ['无法', '购物', '售后'] / ['无法', '购物', '售后']。 |
| ReplyCompleteness | 1.00 ██████████ | PASS | deterministic | 完整性：命中 3/3 个要点 ['无法', '购物', '售后']，缺失 []。 |
| ReplyPoliteness | 0.67 ███████░░░ | PASS | deterministic | 礼貌度：命中客服礼貌用语 ['您', '帮您']。 |
| ToolCorrectness | 1.00 ██████████ | PASS | deterministic | 无需工具，也未调用工具。 |

### 轨迹级 Trajectory Scores

| 指标 | 分数 | 结果 | 来源 | 理由 |
| --- | --- | --- | --- | --- |
| TaskCompletion | 1.00 ██████████ | PASS | deterministic | 任务：识别超范围请求，拒绝天气/写诗并引导回客服场景。。意图正确，路由正确，要点覆盖 100%。路径=['intent_preprocess', 'supervisor', 'reply_generate']，工具=[]。 |
| StepEfficiency | 1.00 ██████████ | PASS | deterministic | 轨迹完全一致：['intent_preprocess', 'supervisor', 'reply_generate'] |

<details><summary>节点 Trace（调试）</summary>

```json
[
  {
    "node": "intent_preprocess",
    "input": {
      "user_query": "明天北京会下雨吗？顺便帮我写一首诗。"
    },
    "output": {
      "intent": "out_of_scope",
      "intent_confidence": 0.8500000000000001,
      "cleaned_query": "明天北京会下雨吗？顺便帮我写一首诗。",
      "entities": {
        "order_id": null,
        "product": null
      }
    },
    "latency_ms": 0.01
  },
  {
    "node": "supervisor",
    "input": {
      "intent": "out_of_scope",
      "entities": {
        "order_id": null,
        "product": null
      }
    },
    "output": {
      "supervisor_intent": "out_of_scope",
      "route": "direct_reply",
      "route_reason": "根据意图 out_of_scope 按路由表分发给 direct_reply"
    },
    "latency_ms": 0.02
  },
  {
    "node": "reply_generate",
    "input": {
      "query": "明天北京会下雨吗？顺便帮我写一首诗。",
      "tool_round": 0
    },
    "output": {
      "action": "final_reply",
      "final_reply": "这个问题超出了我的职责范围，我这边主要处理购物、物流、退换货和账号售后。如果您有订单或商品相关的问题，我很乐意继续帮您。"
    },
    "latency_ms": 0.15
  }
]
```

</details>

## 3. 用例 `tc_watch_compat` — PASS

**用户**：星云手表 S2 能单独打电话吗？安卓手机能用吗？

**任务**：检索手表规格，准确回答通话能力和系统兼容性。

**最终回复**：您好，星云手表 S2 不支持独立通话，需连接手机使用；兼容 Android 10+ 与 iOS 15+。您可以继续问我续航或表带问题。

**实际路径**：`intent_preprocess → supervisor → rag_retrieve → reply_generate`

**期望路径**：`intent_preprocess → supervisor → rag_retrieve → reply_generate`

### 节点级 Component Scores

| 节点/指标 | 分数 | 结果 | 来源 | 理由 |
| --- | --- | --- | --- | --- |
| IntentAccuracy | 1.00 ██████████ | PASS | deterministic | 预测意图 `product_inquiry` 与标注 `product_inquiry` 一致。 |
| RoutingCorrectness | 1.00 ██████████ | PASS | deterministic | Supervisor 路由 `rag_agent` 与标注 `rag_agent` 一致（意图=product_inquiry）。 |
| RAGQuality | 0.80 ████████░░ | PASS | deterministic | 检索命中 ['kb_watch_s2']。召回=1.00 精确=0.33 F1=0.50 综合=0.80。 多余: kb_wh100_specs,kb_warranty |
| ReplyRelevancy | 1.00 ██████████ | PASS | deterministic | 回复是否覆盖用户问题：要点命中 ['不支持独立通话', 'Android 10'] / ['不支持独立通话', 'Android 10']。 |
| ReplyCompleteness | 1.00 ██████████ | PASS | deterministic | 完整性：命中 2/2 个要点 ['不支持独立通话', 'Android 10']，缺失 []。 |
| ReplyPoliteness | 1.00 ██████████ | PASS | deterministic | 礼貌度：命中客服礼貌用语 ['您', '您好', '可以']。 |
| ToolCorrectness | 1.00 ██████████ | PASS | deterministic | 无需工具，也未调用工具。 |

### 轨迹级 Trajectory Scores

| 指标 | 分数 | 结果 | 来源 | 理由 |
| --- | --- | --- | --- | --- |
| TaskCompletion | 1.00 ██████████ | PASS | deterministic | 任务：检索手表规格，准确回答通话能力和系统兼容性。。意图正确，路由正确，要点覆盖 100%。路径=['intent_preprocess', 'supervisor', 'rag_retrieve', 'reply_generate']，工具=[]。 |
| StepEfficiency | 1.00 ██████████ | PASS | deterministic | 轨迹完全一致：['intent_preprocess', 'supervisor', 'rag_retrieve', 'reply_generate'] |

<details><summary>节点 Trace（调试）</summary>

```json
[
  {
    "node": "intent_preprocess",
    "input": {
      "user_query": "星云手表 S2 能单独打电话吗？安卓手机能用吗？"
    },
    "output": {
      "intent": "product_inquiry",
      "intent_confidence": 0.95,
      "cleaned_query": "星云手表 S2 能单独打电话吗？安卓手机能用吗？",
      "entities": {
        "order_id": null,
        "product": "星云手表 S2"
      }
    },
    "latency_ms": 0.02
  },
  {
    "node": "supervisor",
    "input": {
      "intent": "product_inquiry",
      "entities": {
        "order_id": null,
        "product": "星云手表 S2"
      }
    },
    "output": {
      "supervisor_intent": "product_inquiry",
      "route": "rag_agent",
      "route_reason": "根据意图 product_inquiry 按路由表分发给 rag_agent"
    },
    "latency_ms": 0.01
  },
  {
    "node": "rag_retrieve",
    "input": {
      "retrieval_query": "星云手表 S2 能单独打电话吗？安卓手机能用吗？"
    },
    "output": {
      "retrieved_doc_ids": [
        "kb_watch_s2",
        "kb_wh100_specs",
        "kb_warranty"
      ],
      "titles": [
        "星云手表 S2 规格与兼容性",
        "星云降噪耳机 Pro（WH-100）规格",
        "全国联保与质保期限"
      ]
    },
    "latency_ms": 0.45
  },
  {
    "node": "reply_generate",
    "input": {
      "query": "星云手表 S2 能单独打电话吗？安卓手机能用吗？",
      "tool_round": 0
    },
    "output": {
      "action": "final_reply",
      "final_reply": "您好，星云手表 S2 不支持独立通话，需连接手机使用；兼容 Android 10+ 与 iOS 15+。您可以继续问我续航或表带问题。"
    },
    "latency_ms": 0.02
  }
]
```

</details>

## 4. 怎么读这份报告

- **IntentAccuracy**：子 Agent 1 是否把用户话分到正确意图。
- **RoutingCorrectness**：Supervisor 是否把请求交给正确的子 Agent。最终回复对、路由错，仍然算生产事故。
- **RAGQuality**：子 Agent 2 检索到的文档是否相关（对照 `relevant_doc_ids`）。
- **Reply\***：子 Agent 3 最终回复的相关性 / 完整性 / 礼貌度。
- **ToolCorrectness**：该调的工具有没有调到。
- **TaskCompletion / StepEfficiency**：整条轨迹是否完成任务、有没有多余节点。

分数来源 `deepeval.GEval` 表示 LLM-as-judge；`deterministic` 表示零配置回退，便于没有 API Key 时仍然能跑通 Demo。

