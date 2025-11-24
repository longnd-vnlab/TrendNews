"""
TrendRadar - Fully Independent Refactored Version

This version is COMPLETELY INDEPENDENT from main.py.
All required functions are re-exported through a compatibility layer.
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

print("=" * 70)
print("TrendRadar - Fully Refactored & Independent Version")
print("=" * 70)
print()

from src.config import VERSION, CONFIG
from src.core import DataFetcher, PushRecordManager
from src.renderers.html_renderer import HTMLRenderer
from src.processors import (
    save_titles_to_file,
    load_frequency_words,
    read_all_today_titles,
    detect_latest_new_titles,
    count_word_frequency,
    matches_word_groups,
)
from src.utils import (
    get_beijing_time,
    ensure_directory_exists,
    format_time_display,
    is_first_crawl_today,
)

from src.notifiers import send_to_notifications
from src.utils.version_check import check_version_update

from pathlib import Path
from typing import Dict, List, Optional, Tuple
import webbrowser


class NewsAnalyzer:
    """
    Fully refactored NewsAnalyzer using modular structure.
    
    Uses refactored modules where available, with legacy functions
    for complex rendering/notification logic (temporary).
    """

    MODE_STRATEGIES = {
        "incremental": {
            "mode_name": "Chế độ tăng dần",
            "description": "Chế độ tăng dần（chỉ quan tâm tin tức mới，无mớigiờkhông推送）",
            "realtime_report_type": "实giờtăng dần",
            "summary_report_type": "当ngàytổng hợp",
            "should_send_realtime": True,
            "should_generate_summary": True,
            "summary_mode": "daily",
        },
        "current": {
            "mode_name": "bảng xếp hạng hiện tạichế độ",
            "description": "bảng xếp hạng hiện tạichế độ（tin tức khớp bảng xếp hạng hiện tại + mớitin tứckhu vực + theogiờ推送）",
            "realtime_report_type": "实giờbảng xếp hạng hiện tại",
            "summary_report_type": "bảng xếp hạng hiện tạitổng hợp",
            "should_send_realtime": True,
            "should_generate_summary": True,
            "summary_mode": "current",
        },
        "daily": {
            "mode_name": "当ngàytổng hợpchế độ",
            "description": "当ngàytổng hợpchế độ（所cókhớptin tức + mớitin tứckhu vực + theogiờ推送）",
            "realtime_report_type": "",
            "summary_report_type": "当ngàytổng hợp",
            "should_send_realtime": False,
            "should_generate_summary": True,
            "summary_mode": "daily",
        },
    }

    def __init__(self):
        self.request_interval = CONFIG["REQUEST_INTERVAL"]
        self.report_mode = CONFIG["REPORT_MODE"]
        self.rank_threshold = CONFIG["RANK_THRESHOLD"]
        self.is_github_actions = os.environ.get("GITHUB_ACTIONS") == "true"
        self.is_docker_container = self._detect_docker_environment()
        self.update_info = None
        self.proxy_url = None
        self._setup_proxy()
        self.data_fetcher = DataFetcher(self.proxy_url)

        if self.is_github_actions:
            self._check_version_update()

    def _detect_docker_environment(self) -> bool:
        try:
            if os.environ.get("DOCKER_CONTAINER") == "true":
                return True
            if os.path.exists("/.dockerenv"):
                return True
            return False
        except Exception:
            return False

    def _should_open_browser(self) -> bool:
        return not self.is_github_actions and not self.is_docker_container

    def _setup_proxy(self) -> None:
        if not self.is_github_actions and CONFIG["USE_PROXY"]:
            self.proxy_url = CONFIG["DEFAULT_PROXY"]
            print("Môi trường cục bộ，sử dụng proxy")
        elif not self.is_github_actions and not CONFIG["USE_PROXY"]:
            print("Môi trường cục bộ，chưa bật proxy")
        else:
            print("GitHub Actionsmôi trường，khôngsử dụng proxy")

    def _check_version_update(self) -> None:
        try:
            need_update, remote_version = check_version_update(
                VERSION, CONFIG["VERSION_CHECK_URL"], self.proxy_url
            )

            if need_update and remote_version:
                self.update_info = {
                    "current_version": VERSION,
                    "remote_version": remote_version,
                }
                print(f"发现mới版本: {remote_version} (hiện tại: {VERSION})")
            else:
                print("版本检查hoàn thành，hiện tạivìmới nhất版本")
        except Exception as e:
            print(f"Kiểm tra phiên bản lỗi: {e}")

    def _get_mode_strategy(self) -> Dict:
        return self.MODE_STRATEGIES.get(self.report_mode, self.MODE_STRATEGIES["daily"])

    def _has_notification_configured(self) -> bool:
        return any([
            (CONFIG["TELEGRAM_BOT_TOKEN"] and CONFIG["TELEGRAM_CHAT_ID"]),
            (CONFIG["EMAIL_FROM"] and CONFIG["EMAIL_PASSWORD"] and CONFIG["EMAIL_TO"]),
        ])

    def _has_valid_content(self, stats: List[Dict], new_titles: Optional[Dict] = None) -> bool:
        if self.report_mode in ["incremental", "current"]:
            return any(stat["count"] > 0 for stat in stats)
        else:
            has_matched_news = any(stat["count"] > 0 for stat in stats)
            has_new_news = bool(new_titles and any(len(titles) > 0 for titles in new_titles.values()))
            return has_matched_news or has_new_news

    def _load_analysis_data(self) -> Optional[Tuple]:
        try:
            current_platform_ids = [platform["id"] for platform in CONFIG["PLATFORMS"]]
            print(f"hiện tại监控平台: {current_platform_ids}")

            all_results, id_to_name, title_info = read_all_today_titles(current_platform_ids)

            if not all_results:
                print("không có找đếntrong ngàycủadữ liệu")
                return None

            total_titles = sum(len(titles) for titles in all_results.values())
            print(f"đọcđến {total_titles} tiêu đề（đãtheohiện tại监控平台lọc）")

            new_titles = detect_latest_new_titles(current_platform_ids)
            word_groups, filter_words = load_frequency_words()

            return (all_results, id_to_name, title_info, new_titles, word_groups, filter_words)
        except Exception as e:
            print(f"dữ liệutảithất bại: {e}")
            return None

    def _prepare_current_title_info(self, results: Dict, time_info: str) -> Dict:
        title_info = {}
        for source_id, titles_data in results.items():
            title_info[source_id] = {}
            for title, title_data in titles_data.items():
                ranks = title_data.get("ranks", [])
                url = title_data.get("url", "")
                mobile_url = title_data.get("mobileUrl", "")

                title_info[source_id][title] = {
                    "first_time": time_info,
                    "last_time": time_info,
                    "count": 1,
                    "ranks": ranks,
                    "url": url,
                    "mobileUrl": mobile_url,
                }
        return title_info

    def _run_analysis_pipeline(
        self, data_source, mode, title_info, new_titles, word_groups,
        filter_words, id_to_name, failed_ids=None, is_daily_summary=False
    ) -> Tuple:
        stats, total_titles = count_word_frequency(
            data_source, word_groups, filter_words, id_to_name,
            title_info, self.rank_threshold, new_titles, mode=mode
        )

        html_file = HTMLRenderer.generate_report(
            stats, total_titles, failed_ids=failed_ids, new_titles=new_titles,
            id_to_name=id_to_name, mode=mode, is_daily_summary=is_daily_summary,
            update_info=self.update_info if CONFIG["SHOW_VERSION_UPDATE"] else None
        )

        return stats, html_file

    def _send_notification_if_needed(
        self, stats, report_type, mode, failed_ids=None,
        new_titles=None, id_to_name=None, html_file_path=None
    ) -> bool:
        has_notification = self._has_notification_configured()

        if CONFIG["ENABLE_NOTIFICATION"] and has_notification and self._has_valid_content(stats, new_titles):
            send_to_notifications(
                stats, failed_ids or [], report_type, new_titles, id_to_name,
                self.update_info, self.proxy_url, mode=mode, html_file_path=html_file_path
            )
            return True
        elif CONFIG["ENABLE_NOTIFICATION"] and not has_notification:
            print("⚠️ cảnh báo：thông báo功能đã启用nhưngChưa cấu hình kênh thông báo nào，sẽbỏ qua gửi thông báo")
        elif not CONFIG["ENABLE_NOTIFICATION"]:
            print(f"bỏ qua{report_type}thông báo：thông báo功能đã禁用")
        elif CONFIG["ENABLE_NOTIFICATION"] and has_notification and not self._has_valid_content(stats, new_titles):
            mode_strategy = self._get_mode_strategy()
            if "实giờ" in report_type:
                print(f"Bỏ qua实giờ推送thông báo：{mode_strategy['mode_name']}dưới未检测đếnkhớpcủatin tức")
            else:
                print(f"Bỏ qua{mode_strategy['summary_report_type']}thông báo：未khớpđếncó效củatin tứcnội dung")

        return False

    def _generate_summary_report(self, mode_strategy: Dict) -> Optional[str]:
        summary_type = "bảng xếp hạng hiện tạitổng hợp" if mode_strategy["summary_mode"] == "current" else "当ngàytổng hợp"
        print(f"tạo{summary_type}báo cáo...")

        analysis_data = self._load_analysis_data()
        if not analysis_data:
            return None

        all_results, id_to_name, title_info, new_titles, word_groups, filter_words = analysis_data

        stats, html_file = self._run_analysis_pipeline(
            all_results, mode_strategy["summary_mode"], title_info, new_titles,
            word_groups, filter_words, id_to_name, is_daily_summary=True
        )

        print(f"{summary_type}báo cáođãtạo: {html_file}")

        self._send_notification_if_needed(
            stats, mode_strategy["summary_report_type"], mode_strategy["summary_mode"],
            failed_ids=[], new_titles=new_titles, id_to_name=id_to_name, html_file_path=html_file
        )

        return html_file

    def _generate_summary_html(self, mode: str = "daily") -> Optional[str]:
        summary_type = "bảng xếp hạng hiện tạitổng hợp" if mode == "current" else "当ngàytổng hợp"
        print(f"tạo{summary_type}HTML...")

        analysis_data = self._load_analysis_data()
        if not analysis_data:
            return None

        all_results, id_to_name, title_info, new_titles, word_groups, filter_words = analysis_data

        _, html_file = self._run_analysis_pipeline(
            all_results, mode, title_info, new_titles, word_groups,
            filter_words, id_to_name, is_daily_summary=True
        )

        print(f"{summary_type}HTMLđãtạo: {html_file}")
        return html_file

    def _initialize_and_check_config(self) -> None:
        now = get_beijing_time()
        print(f"hiện tại北京thời gian: {now.strftime('%Y-%m-%d %H:%M:%S')}")

        if not CONFIG["ENABLE_CRAWLER"]:
            print("爬虫功能đã禁用（ENABLE_CRAWLER=False），Chương trình thoát")
            return

        has_notification = self._has_notification_configured()
        if not CONFIG["ENABLE_NOTIFICATION"]:
            print("thông báo功能đã禁用（ENABLE_NOTIFICATION=False），sẽ只进行dữ liệu抓取")
        elif not has_notification:
            print("Chưa cấu hình kênh thông báo nào，sẽ只进行dữ liệu抓取，khônggửithông báo")
        else:
            print("thông báo功能đã启用，sẽgửithông báo")

        mode_strategy = self._get_mode_strategy()
        print(f"báo cáoChế độ: {self.report_mode}")
        print(f"运行Chế độ: {mode_strategy['description']}")

    def _crawl_data(self) -> Tuple:
        ids = []
        for platform in CONFIG["PLATFORMS"]:
            if "name" in platform:
                ids.append((platform["id"], platform["name"]))
            else:
                ids.append(platform["id"])

        print(f"配置của监控平台: {[p.get('name', p['id']) for p in CONFIG['PLATFORMS']]}")
        print(f"bắt đầuthu thậpdữ liệu，Yêu cầu间隔 {self.request_interval} mili giây")
        ensure_directory_exists("output")

        results, id_to_name, failed_ids = self.data_fetcher.crawl_websites(ids, self.request_interval)

        title_file = save_titles_to_file(results, id_to_name, failed_ids)
        print(f"标题đãlưuđến: {title_file}")

        return results, id_to_name, failed_ids

    def _execute_mode_strategy(self, mode_strategy, results, id_to_name, failed_ids) -> Optional[str]:
        current_platform_ids = [platform["id"] for platform in CONFIG["PLATFORMS"]]

        new_titles = detect_latest_new_titles(current_platform_ids)
        time_info = Path(save_titles_to_file(results, id_to_name, failed_ids)).stem
        word_groups, filter_words = load_frequency_words()

        if self.report_mode == "current":
            analysis_data = self._load_analysis_data()
            if analysis_data:
                all_results, historical_id_to_name, historical_title_info, historical_new_titles, _, _ = analysis_data

                print(f"currentchế độ：Sử dụnglọc后của历史数据，bao gồm nền tảng：{list(all_results.keys())}")

                stats, html_file = self._run_analysis_pipeline(
                    all_results, self.report_mode, historical_title_info, historical_new_titles,
                    word_groups, filter_words, historical_id_to_name, failed_ids=failed_ids
                )

                combined_id_to_name = {**historical_id_to_name, **id_to_name}

                print(f"HTMLbáo cáođãtạo: {html_file}")

                summary_html = None
                if mode_strategy["should_send_realtime"]:
                    self._send_notification_if_needed(
                        stats, mode_strategy["realtime_report_type"], self.report_mode,
                        failed_ids=failed_ids, new_titles=historical_new_titles,
                        id_to_name=combined_id_to_name, html_file_path=html_file
                    )
            else:
                print("❌ 严重lỗi：无法đọc刚lưucủadữ liệufile")
                raise RuntimeError("数据một致性检查失败：Đọc ngay sau khi lưu thất bại")
        else:
            title_info = self._prepare_current_title_info(results, time_info)
            stats, html_file = self._run_analysis_pipeline(
                results, self.report_mode, title_info, new_titles,
                word_groups, filter_words, id_to_name, failed_ids=failed_ids
            )
            print(f"HTMLbáo cáođãtạo: {html_file}")

            summary_html = None
            if mode_strategy["should_send_realtime"]:
                self._send_notification_if_needed(
                    stats, mode_strategy["realtime_report_type"], self.report_mode,
                    failed_ids=failed_ids, new_titles=new_titles,
                    id_to_name=id_to_name, html_file_path=html_file
                )

        summary_html = None
        if mode_strategy["should_generate_summary"]:
            if mode_strategy["should_send_realtime"]:
                summary_html = self._generate_summary_html(mode_strategy["summary_mode"])
            else:
                summary_html = self._generate_summary_report(mode_strategy)

        if self._should_open_browser() and html_file:
            if summary_html:
                summary_url = "file://" + str(Path(summary_html).resolve())
                print(f"正ởmởtổng hợpbáo cáo: {summary_url}")
                webbrowser.open(summary_url)
            else:
                file_url = "file://" + str(Path(html_file).resolve())
                print(f"正ởmởHTMLbáo cáo: {file_url}")
                webbrowser.open(file_url)
        elif self.is_docker_container and html_file:
            if summary_html:
                print(f"tổng hợpbáo cáođãtạo（Dockermôi trường）: {summary_html}")
            else:
                print(f"HTMLbáo cáođãtạo（Dockermôi trường）: {html_file}")

        return summary_html

    def run(self) -> None:
        try:
            self._initialize_and_check_config()
            mode_strategy = self._get_mode_strategy()
            results, id_to_name, failed_ids = self._crawl_data()
            self._execute_mode_strategy(mode_strategy, results, id_to_name, failed_ids)
        except Exception as e:
            print(f"phân tích流程执行出错: {e}")
            raise


def main():
    try:
        print("Using refactored modular structure with legacy function compatibility")
        print()
        analyzer = NewsAnalyzer()
        analyzer.run()
        return True
    except FileNotFoundError as e:
        print(f"❌ File cấu hìnhlỗi: {e}")
        print("\nVui lòng đảm bảo các file sau tồn tại:")
        print("  • config/config.yaml")
        print("  • config/frequency_words.txt")
        return False
    except Exception as e:
        print(f"❌ Lỗi chạy chương trình: {e}")
        raise


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
