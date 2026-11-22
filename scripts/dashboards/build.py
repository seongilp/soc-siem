#!/usr/bin/env python3
"""SIEM 개요 대시보드 saved objects(ndjson) 생성기.

    python3 scripts/dashboards/build.py > scripts/dashboards/siem-overview.ndjson

결과물은 dashboards-init 이 Dashboards 로 import 한다.
"""
import json
import sys

OSD_VERSION = "3.10.0"
AUTH = "siem-linux-auth"      # index-pattern id (bootstrap.sh 가 생성)
WEB = "siem-web-access"
INDEX_REF = "kibanaSavedObjectMeta.searchSourceJSON.index"
GRID_COLUMNS = 48


def search_source(query):
    return json.dumps({
        "query": {"query": query, "language": "kuery"},
        "filter": [],
        "indexRefName": INDEX_REF,
    })


def index_ref(pattern):
    return [{"name": INDEX_REF, "type": "index-pattern", "id": pattern}]


def count(label):
    return {"id": "1", "enabled": True, "type": "count", "schema": "metric",
            "params": {"customLabel": label}}


def terms(agg_id, schema, field, label, size=10):
    return {"id": agg_id, "enabled": True, "type": "terms", "schema": schema,
            "params": {"field": field, "orderBy": "1", "order": "desc", "size": size,
                       "otherBucket": False, "missingBucket": False, "customLabel": label}}


def date_histogram():
    return {"id": "2", "enabled": True, "type": "date_histogram", "schema": "segment",
            "params": {"field": "@timestamp", "useNormalizedOpenSearchInterval": True,
                       "interval": "auto", "drop_partials": False, "min_doc_count": 1,
                       "extended_bounds": {}, "customLabel": "시간"}}


def visualization(vis_id, title, pattern, query, vis_type, params, aggs):
    vis_state = {"title": title, "type": vis_type, "params": params, "aggs": aggs}
    return {
        "type": "visualization",
        "id": vis_id,
        "attributes": {
            "title": title,
            "description": "",
            "version": 1,
            "uiStateJSON": "{}",
            "visState": json.dumps(vis_state, ensure_ascii=False),
            "kibanaSavedObjectMeta": {"searchSourceJSON": search_source(query)},
        },
        "references": index_ref(pattern),
    }


def metric(vis_id, title, pattern, query, label):
    params = {
        "type": "metric", "addTooltip": True, "addLegend": False,
        "metric": {
            "percentageMode": False, "useRanges": False, "colorSchema": "Green to Red",
            "metricColorMode": "None", "colorsRange": [{"from": 0, "to": 10000}],
            "labels": {"show": True}, "invertColors": False,
            "style": {"bgFill": "#000", "bgColor": False, "labelColor": False,
                      "subText": "", "fontSize": 40},
        },
    }
    return visualization(vis_id, title, pattern, query, "metric", params, [count(label)])


def table(vis_id, title, pattern, query, columns, metric_label="건수"):
    """columns: [(field, label), ...] — 순서대로 terms 버킷 컬럼이 된다."""
    params = {"perPage": 10, "showPartialRows": False, "showMetricsAtAllLevels": False,
              "sort": {"columnIndex": None, "direction": None},
              "showTotal": False, "totalFunc": "sum", "percentageCol": ""}
    buckets = [terms(str(i + 2), "bucket", field, label)
               for i, (field, label) in enumerate(columns)]
    return visualization(vis_id, title, pattern, query, "table", params,
                         [count(metric_label), *buckets])


def donut(vis_id, title, pattern, query, field, label):
    params = {"type": "pie", "addTooltip": True, "addLegend": True,
              "legendPosition": "right", "isDonut": True,
              "labels": {"show": False, "values": True, "last_level": True, "truncate": 100}}
    return visualization(vis_id, title, pattern, query, "pie", params,
                         [count("건수"), terms("2", "segment", field, label)])


def stacked_timeline(vis_id, title, pattern, query, split_field, split_label):
    params = {
        "type": "histogram",
        "grid": {"categoryLines": False},
        "categoryAxes": [{
            "id": "CategoryAxis-1", "type": "category", "position": "bottom", "show": True,
            "style": {}, "scale": {"type": "linear"},
            "labels": {"show": True, "filter": True, "truncate": 100}, "title": {},
        }],
        "valueAxes": [{
            "id": "ValueAxis-1", "name": "LeftAxis-1", "type": "value", "position": "left",
            "show": True, "style": {}, "scale": {"type": "linear", "mode": "normal"},
            "labels": {"show": True, "rotate": 0, "filter": False, "truncate": 100},
            "title": {"text": "건수"},
        }],
        "seriesParams": [{
            "show": True, "type": "histogram", "mode": "stacked",
            "data": {"label": "건수", "id": "1"}, "valueAxis": "ValueAxis-1",
            "drawLinesBetweenPoints": True, "showCircles": True,
        }],
        "addTooltip": True, "addLegend": True, "legendPosition": "right",
        "times": [], "addTimeMarker": False, "labels": {"show": False},
        "thresholdLine": {"show": False, "value": 10, "width": 1, "style": "full",
                          "color": "#E7664C"},
    }
    aggs = [count("건수"), date_histogram(), terms("3", "group", split_field, split_label, 5)]
    return visualization(vis_id, title, pattern, query, "histogram", params, aggs)


def saved_search(search_id, title, pattern, query, columns):
    return {
        "type": "search",
        "id": search_id,
        "attributes": {
            "title": title, "description": "", "version": 1,
            "columns": columns, "sort": [["@timestamp", "desc"]],
            "kibanaSavedObjectMeta": {"searchSourceJSON": search_source(query)},
        },
        "references": index_ref(pattern),
    }


def dashboard(dash_id, title, description, rows):
    """rows: [(height, [(saved_object, width), ...]), ...] — 위에서 아래, 왼쪽에서 오른쪽."""
    panels, references = [], []
    y = 0
    for height, cells in rows:
        if sum(width for _, width in cells) > GRID_COLUMNS:
            raise ValueError(f"행 너비가 {GRID_COLUMNS} 를 넘습니다: {[o['id'] for o, _ in cells]}")
        x = 0
        for obj, width in cells:
            index = len(panels)
            panels.append({
                "version": OSD_VERSION,
                "gridData": {"x": x, "y": y, "w": width, "h": height, "i": str(index)},
                "panelIndex": str(index),
                "embeddableConfig": {},
                "panelRefName": f"panel_{index}",
            })
            references.append({"name": f"panel_{index}", "type": obj["type"], "id": obj["id"]})
            x += width
        y += height
    return {
        "type": "dashboard",
        "id": dash_id,
        "attributes": {
            "title": title, "description": description, "version": 1,
            "panelsJSON": json.dumps(panels),
            "optionsJSON": json.dumps({"hidePanelTitles": False, "useMargins": True}),
            "timeRestore": True, "timeFrom": "now-24h", "timeTo": "now",
            "refreshInterval": {"pause": False, "value": 30000},
            "kibanaSavedObjectMeta": {"searchSourceJSON": json.dumps(
                {"query": {"query": "", "language": "kuery"}, "filter": []})},
        },
        "references": references,
    }


def build():
    failed, accepted, client_error = "event_action:Failed", "event_action:Accepted", "http_status >= 400"

    m_failed = metric("siem-m-ssh-failed", "SSH 로그인 실패", AUTH, failed, "실패")
    m_accepted = metric("siem-m-ssh-accepted", "SSH 로그인 성공", AUTH, accepted, "성공")
    m_web = metric("siem-m-web-requests", "웹 요청", WEB, "", "요청")
    m_web_err = metric("siem-m-web-errors", "웹 4xx/5xx", WEB, client_error, "오류 응답")

    t_auth = stacked_timeline("siem-ts-ssh-auth", "SSH 인증 추이 (결과별)", AUTH,
                              "event_action:*", "event_action", "결과")
    t_web = stacked_timeline("siem-ts-web-status", "웹 요청 추이 (상태 코드별)", WEB,
                             "", "http_status", "상태 코드")

    tb_src = table("siem-tb-ssh-sources", "SSH 실패 출발지 IP Top 10", AUTH, failed,
                   [("source_ip", "출발지 IP")], "실패")
    tb_users = table("siem-tb-ssh-users", "공격 대상 계정 Top 10", AUTH, failed,
                     [("user_name", "계정")], "실패")
    tb_success = table("siem-tb-ssh-success", "SSH 로그인 성공 (계정 · 출발지)", AUTH, accepted,
                       [("user_name", "계정"), ("source_ip", "출발지 IP")], "성공")

    tb_paths = table("siem-tb-web-paths", "오류 응답 요청 경로 Top 10", WEB, client_error,
                     [("url_original", "요청"), ("http_status", "상태")])
    tb_web_src = table("siem-tb-web-sources", "웹 오류 유발 출발지 · User-Agent", WEB, client_error,
                       [("source_ip", "출발지 IP"), ("user_agent", "User-Agent")])
    d_status = donut("siem-pie-web-status", "HTTP 상태 코드 분포", WEB, "", "http_status", "상태 코드")

    s_auth = saved_search("siem-s-ssh-events", "최근 SSH 인증 이벤트", AUTH, "event_action:*",
                          ["event_action", "user_name", "source_ip", "auth_method", "host"])

    dash = dashboard(
        "siem-overview", "SIEM 개요",
        "SSH 인증과 웹 접근 로그 요약 (soc-siem 랩)",
        [
            (7, [(m_failed, 12), (m_accepted, 12), (m_web, 12), (m_web_err, 12)]),
            (13, [(t_auth, 24), (t_web, 24)]),
            (13, [(tb_src, 16), (tb_users, 16), (tb_success, 16)]),
            (13, [(tb_paths, 20), (tb_web_src, 16), (d_status, 12)]),
            (14, [(s_auth, 48)]),
        ],
    )
    return [m_failed, m_accepted, m_web, m_web_err, t_auth, t_web, tb_src, tb_users,
            tb_success, tb_paths, tb_web_src, d_status, s_auth, dash]


if __name__ == "__main__":
    for saved_object in build():
        sys.stdout.write(json.dumps(saved_object, ensure_ascii=False) + "\n")
