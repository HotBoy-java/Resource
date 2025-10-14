#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
PotatoTool 自动化资源更新脚本
用于自动更新 JAR 文件、资源文件和 manifest.json，并推送到 GitHub
@author Potato
@date 2025-10-12
"""

import os
import sys
import json
import hashlib
import shutil
import subprocess
import re
import zipfile
import csv
import io
from datetime import datetime
from pathlib import Path
from urllib.request import urlretrieve

# 配置项
CONFIG = {
    'jar_source_dir': '/Users/a/Desktop/项目开发/PotatoTool/outJar',
    'project_dir': os.path.dirname(os.path.dirname(os.path.abspath(__file__))),  # 项目根目录
    'data_dir': os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'data'),  # data 目录
    'github_release_base': 'https://github.com/HotBoy-java/PotatoTool/releases/download',
    'mirror_base': 'http://potato.gold:16668/releases',
    'resource_mirror_base': 'http://potato.gold:16668/resources',
}

class ColorPrint:
    """彩色打印输出"""
    
    @staticmethod
    def info(msg):
        print(f'\033[7;34m[信息]\033[0m \033[0;34m{msg}\033[0m')
    
    @staticmethod
    def success(msg):
        print(f'\033[0;42m[成功]\033[0m \033[0;32m{msg}\033[0m')
    
    @staticmethod
    def warning(msg):
        print(f'\033[0;43m[警告]\033[0m \033[0;33m{msg}\033[0m')
    
    @staticmethod
    def error(msg):
        print(f'\033[7;31m[错误]\033[0m \033[0;31m{msg}\033[0m')
    
    @staticmethod
    def process(msg):
        print(f'\033[7;35m[处理]\033[0m {msg}')

class FileHashCalculator:
    """文件哈希计算器"""
    
    @staticmethod
    def calculate_hash(file_path, hash_type='sha256'):
        """计算文件哈希值"""
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"文件不存在: {file_path}")
        
        hash_obj = hashlib.sha256() if hash_type == 'sha256' else hashlib.md5()
        
        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(8192), b""):
                hash_obj.update(chunk)
        
        return hash_obj.hexdigest()
    
    @staticmethod
    def get_file_info(file_path):
        """获取文件完整信息"""
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"文件不存在: {file_path}")
        
        size = os.path.getsize(file_path)
        sha256 = FileHashCalculator.calculate_hash(file_path, 'sha256')
        md5 = FileHashCalculator.calculate_hash(file_path, 'md5')
        
        return {
            'size': size,
            'sha256': sha256,
            'md5': md5
        }

class JarFileManager:
    """JAR 文件管理器"""
    
    def __init__(self, source_dir):
        self.source_dir = source_dir
    
    def find_latest_jars(self):
        """查找最新的 JAR 文件"""
        ColorPrint.process("正在查找最新的 JAR 文件...")
        
        if not os.path.exists(self.source_dir):
            raise FileNotFoundError(f"源目录不存在: {self.source_dir}")
        
        jar_files = []
        # 支持多种命名格式：jdk8, jdk11+
        pattern = re.compile(r'PotatoTool-(\d+\.\d+)-(jdk8|jdk11\+)\.jar')
        
        for filename in os.listdir(self.source_dir):
            match = pattern.match(filename)
            if match:
                version = match.group(1)
                jdk_suffix = match.group(2)
                
                # 标准化 JDK 类型
                if jdk_suffix == 'jdk8':
                    jdk_type = '8'
                elif jdk_suffix.startswith('jdk11'):
                    jdk_type = '11+'
                else:
                    continue
                
                file_path = os.path.join(self.source_dir, filename)
                file_stat = os.stat(file_path)
                
                jar_files.append({
                    'filename': filename,
                    'version': version,
                    'jdk_type': jdk_type,
                    'path': file_path,
                    'mtime': file_stat.st_mtime,
                    'size': file_stat.st_size
                })
        
        if not jar_files:
            raise FileNotFoundError(f"在 {self.source_dir} 中未找到 JAR 文件")
        
        # 按版本和修改时间排序，获取最新版本
        jar_files.sort(key=lambda x: (x['version'], x['mtime']), reverse=True)
        
        # 获取最新的 jdk8 和 jdk11 文件
        jdk8_jar = None
        jdk11_jar = None
        
        for jar in jar_files:
            if jar['jdk_type'] == '8' and not jdk8_jar:
                jdk8_jar = jar
            elif jar['jdk_type'] == '11+' and not jdk11_jar:
                jdk11_jar = jar
            
            if jdk8_jar and jdk11_jar:
                break
        
        # 确定最终版本号
        if jdk8_jar and jdk11_jar:
            # 使用较新的那个版本号
            if jdk8_jar['mtime'] > jdk11_jar['mtime']:
                latest_version = jdk8_jar['version']
            else:
                latest_version = jdk11_jar['version']
        elif jdk8_jar:
            latest_version = jdk8_jar['version']
            ColorPrint.warning(f"⚠️  未找到 JDK11+ 版本，仅使用 JDK8 版本")
        elif jdk11_jar:
            latest_version = jdk11_jar['version']
            ColorPrint.warning(f"⚠️  未找到 JDK8 版本，仅使用 JDK11+ 版本")
        else:
            raise FileNotFoundError(f"未找到任何有效的 JAR 文件")
        
        ColorPrint.success(f"找到最新版本: {latest_version}")
        if jdk8_jar:
            ColorPrint.info(f"  - JDK8:  {jdk8_jar['filename']} ({jdk8_jar['size']:,} 字节)")
        if jdk11_jar:
            ColorPrint.info(f"  - JDK11+: {jdk11_jar['filename']} ({jdk11_jar['size']:,} 字节)")
        
        return latest_version, jdk8_jar, jdk11_jar
    
    def get_jar_info(self, jdk8_jar, jdk11_jar):
        """获取 JAR 文件信息（不复制文件）"""
        ColorPrint.process("正在读取 JAR 文件信息...")
        
        jar_info = {}
        
        if jdk8_jar:
            jar_info['jdk8'] = {
                'path': jdk8_jar['path'],
                'filename': jdk8_jar['filename'],
                'info': FileHashCalculator.get_file_info(jdk8_jar['path'])
            }
            ColorPrint.success(f"已读取 JDK8 版本: {jdk8_jar['filename']}")
        
        if jdk11_jar:
            jar_info['jdk11'] = {
                'path': jdk11_jar['path'],
                'filename': jdk11_jar['filename'],
                'info': FileHashCalculator.get_file_info(jdk11_jar['path'])
            }
            ColorPrint.success(f"已读取 JDK11+ 版本: {jdk11_jar['filename']}")
        
        return jar_info

class WinKbInfoUpdater:
    """Windows KB 信息更新器"""
    
    def __init__(self, data_dir):
        self.data_dir = data_dir
        # 确保 data 目录存在
        os.makedirs(self.data_dir, exist_ok=True)
    
    def download_definitions(self):
        """下载 Windows KB 定义文件"""
        ColorPrint.process("正在下载 Windows KB 定义文件...")
        
        zip_path = os.path.join(self.data_dir, 'winKbInfo.zip')
        try:
            urlretrieve('https://raw.githubusercontent.com/bitsadmin/wesng/master/definitions.zip', zip_path)
            ColorPrint.success("定义文件下载完成")
            return zip_path
        except Exception as e:
            ColorPrint.error(f"下载失败: {str(e)}")
            raise
    
    def load_definitions(self, zip_path):
        """加载并解析定义文件"""
        ColorPrint.process("正在解析定义文件...")
        
        with zipfile.ZipFile(zip_path, 'r') as definitionszip:
            files = definitionszip.namelist()
            
            # CVEs_yyyyMMdd.csv
            cvesfiles = list(filter(lambda f: f.startswith('CVEs'), files))
            cvesfile = cvesfiles[0]
            dateStr = cvesfile.split('.')[0].split('_')[1]
            f = io.TextIOWrapper(definitionszip.open(cvesfile, 'r'))
            cves = csv.DictReader(filter(lambda row: row[0] != '#', f), delimiter=str(','), quotechar=str('"'))
            
            # Custom_yyyyMMdd.csv
            customfiles = list(filter(lambda f: f.startswith('Custom'), files))
            customfile = customfiles[0]
            f = io.TextIOWrapper(definitionszip.open(customfile, 'r'))
            custom = csv.DictReader(filter(lambda row: row[0] != '#', f), delimiter=str(','), quotechar=str('"'))
            
            # 合并官方和自定义 CVE 列表
            merged = [cve for cve in cves] + [c for c in custom]
            
            ColorPrint.success(f"解析完成，版本日期: {dateStr}")
            return merged, dateStr
    
    def save_csv(self, cves, date_str):
        """保存 CSV 文件"""
        ColorPrint.process("正在保存 CSV 文件...")
        
        # 新文件名（不带时间后缀，便于管理）
        filename = "winKbInfo.csv"
        filepath = os.path.join(self.data_dir, filename)
        
        # 删除旧的 winKbInfo*.csv 文件
        pattern = r'^winKbInfo.*\.csv$'
        for old_file in os.listdir(self.data_dir):
            if re.match(pattern, old_file):
                old_path = os.path.join(self.data_dir, old_file)
                if old_path != filepath:
                    os.remove(old_path)
                    ColorPrint.info(f"已删除旧文件: {old_file}")
        
        # 保存新文件
        rows = [list(cve.values()) for cve in cves]
        
        with open(filepath, 'w', newline='', encoding='utf-8') as csvfile:
            writer = csv.writer(csvfile)
            writer.writerow(["发布日期", "CVE编号", "KB编号", "标题", "影响产品", "影响组件", "严重性", "漏洞影响", "替代KB编号", "漏洞利用"])
            writer.writerows(rows)
        
        ColorPrint.success(f"CSV 文件已保存: {filename} (版本: {date_str})")
        return filepath, date_str
    
    def update(self):
        """执行完整的更新流程"""
        try:
            zip_path = self.download_definitions()
            cves, date_str = self.load_definitions(zip_path)
            csv_path, date_str = self.save_csv(cves, date_str)
            
            # 清理临时文件
            if os.path.exists(zip_path):
                os.remove(zip_path)
            
            return csv_path, date_str
        except Exception as e:
            ColorPrint.error(f"WinKbInfo 更新失败: {str(e)}")
            return None, None

class ManifestGenerator:
    """Manifest 清单生成器"""
    
    def __init__(self, project_dir, data_dir):
        self.project_dir = project_dir
        self.data_dir = data_dir
        self.manifest_path = os.path.join(project_dir, 'manifest.json')
        self.old_manifest = self.load_old_manifest()
    
    def load_old_manifest(self):
        """加载现有的 manifest.json"""
        if os.path.exists(self.manifest_path):
            try:
                with open(self.manifest_path, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception as e:
                ColorPrint.warning(f"无法读取旧的 manifest.json: {str(e)}")
                return None
        return None
    
    def check_changes(self, version, jar_info, winkb_info):
        """检查资源是否有变化
        返回: (has_changes, changes_list)
        """
        if not self.old_manifest:
            return True, ["首次生成 manifest.json"]
        
        changes = []
        
        # 检查 JAR 版本
        old_version = self.old_manifest.get('app', {}).get('version', '')
        if version != old_version:
            changes.append(f"JAR 版本变化: {old_version} → {version}")
        
        # 检查 JDK8 文件哈希
        if 'jdk8' in jar_info:
            old_jdk8_sha256 = self.old_manifest.get('app', {}).get('files', {}).get('jdk8', {}).get('checksum', {}).get('sha256', '')
            new_jdk8_sha256 = jar_info['jdk8']['info']['sha256']
            if old_jdk8_sha256 != new_jdk8_sha256:
                changes.append(f"JDK8 文件已更新")
        
        # 检查 JDK11 文件哈希
        if 'jdk11' in jar_info:
            old_jdk11_sha256 = self.old_manifest.get('app', {}).get('files', {}).get('jdk11', {}).get('checksum', {}).get('sha256', '')
            new_jdk11_sha256 = jar_info['jdk11']['info']['sha256']
            if old_jdk11_sha256 != new_jdk11_sha256:
                changes.append(f"JDK11 文件已更新")
        
        # 检查 WinKbInfo 版本（只对比版本号，不对比哈希）
        winkb_path, winkb_date = winkb_info
        if winkb_path and winkb_date:
            old_winkb_version = None
            for resource in self.old_manifest.get('resources', []):
                if resource.get('name') == 'winKbInfo':
                    old_winkb_version = resource.get('version', '')
                    break
            
            # 对比版本号判断是否有更新
            if old_winkb_version != winkb_date:
                changes.append(f"WinKbInfo 已更新: {old_winkb_version} → {winkb_date}")
        
        # 检查 MD5 数据库（通过 .db 文件哈希判断）
        md5_db_result = self.find_md5_database()
        if md5_db_result:
            gzip_path, db_path = md5_db_result
            
            # 获取旧的 MD5 数据库信息（从 manifest.json）
            old_md5_hash = None
            old_md5_version = None
            for resource in self.old_manifest.get('resources', []):
                if resource.get('name') == 'md5':
                    old_md5_version = resource.get('version', '')
                    old_md5_hash = resource.get('files', {}).get('checksum', {}).get('sha256', '')
                    break
            
            # 计算当前 .db 文件的哈希（不是 .gzip）
            if os.path.exists(db_path):
                new_md5_info = FileHashCalculator.get_file_info(db_path)
                new_md5_hash = new_md5_info['sha256']
                
                # 对比哈希值判断文件是否变化
                if old_md5_hash and old_md5_hash != new_md5_hash:
                    # 文件已更新
                    changes.append(f"MD5 数据库文件已更新（.db 文件内容已变化）")
                elif not old_md5_hash:
                    # 首次添加
                    changes.append(f"MD5 数据库：首次添加")
        
        return len(changes) > 0, changes
    
    def generate(self, version, jar_info, winkb_info, changelog=None):
        """生成 manifest.json"""
        ColorPrint.process("正在生成 manifest.json...")
        
        # jar_info 已经包含了完整信息，直接使用
        files_info = jar_info
        
        # 计算 winKbInfo 文件信息
        winkb_path, winkb_date = winkb_info
        winkb_filename = os.path.basename(winkb_path) if winkb_path else "winKbInfo.csv"
        winkb_file_info = FileHashCalculator.get_file_info(winkb_path) if winkb_path and os.path.exists(winkb_path) else None
        
        # 获取当前时间
        now = datetime.now()
        
        # 默认更新日志
        if changelog is None:
            changelog = [
                f"更新时间: {now.strftime('%Y-%m-%d %H:%M:%S')}",
                "自动更新 JAR 文件",
                "自动更新资源文件"
            ]
        
        # 构建 manifest
        manifest = {
            "version": "2.0",
            "lastUpdate": now.strftime('%Y-%m-%dT%H:%M:%SZ'),
            "app": {
                "version": version,
                "releaseDate": now.strftime('%Y-%m-%d'),
                "changelog": changelog,
                "required": False,
                "files": {}
            },
            "resources": []
        }
        
        # 添加 JAR 文件信息
        if 'jdk8' in files_info:
            manifest["app"]["files"]["jdk8"] = {
                "url": {
                    "github": f"{CONFIG['github_release_base']}/v{version}/{files_info['jdk8']['filename']}",
                    "mirror": f"{CONFIG['mirror_base']}/{files_info['jdk8']['filename']}"
                },
                "size": files_info['jdk8']['info']['size'],
                "checksum": {
                    "sha256": files_info['jdk8']['info']['sha256'],
                    "md5": files_info['jdk8']['info']['md5']
                }
            }
        
        if 'jdk11' in files_info:
            manifest["app"]["files"]["jdk11"] = {
                "url": {
                    "github": f"{CONFIG['github_release_base']}/v{version}/{files_info['jdk11']['filename']}",
                    "mirror": f"{CONFIG['mirror_base']}/{files_info['jdk11']['filename']}"
                },
                "size": files_info['jdk11']['info']['size'],
                "checksum": {
                    "sha256": files_info['jdk11']['info']['sha256'],
                    "md5": files_info['jdk11']['info']['md5']
                }
            }
        
        # 添加 md5_database 资源（如果存在）
        md5_db_result = self.find_md5_database()
        if md5_db_result:
            gzip_path, db_path = md5_db_result
            
            # 计算解压后的 .db 文件的校验和和大小
            md5_db_info = FileHashCalculator.get_file_info(db_path)
            
            # 获取压缩文件的大小（用于下载）
            gzip_size = os.path.getsize(gzip_path)
            
            # 使用 gzip 文件名（用于 URL）
            md5_db_filename = os.path.basename(gzip_path)
            
            # 确定版本号：
            # 1. 优先从文件名提取日期
            # 2. 如果文件哈希变化，使用当前日期
            # 3. 如果文件哈希未变化，保持旧版本号
            md5_version_match = re.search(r'_(\d{8})', md5_db_filename)
            
            if md5_version_match:
                # 文件名中有日期，直接使用
                md5_version = md5_version_match.group(1)
            else:
                # 文件名中没有日期，根据哈希判断
                old_md5_hash = None
                old_md5_version = None
                if self.old_manifest:
                    for resource in self.old_manifest.get('resources', []):
                        if resource.get('name') == 'md5':
                            old_md5_version = resource.get('version', '')
                            old_md5_hash = resource.get('files', {}).get('checksum', {}).get('sha256', '')
                            break
                
                # 对比当前 .db 文件的哈希
                current_md5_hash = md5_db_info['sha256']
                
                if old_md5_hash and old_md5_hash == current_md5_hash:
                    # 文件未变化，保持旧版本号
                    md5_version = old_md5_version if old_md5_version else now.strftime('%Y%m%d')
                    ColorPrint.info(f"MD5 数据库内容未变化，保持版本号: {md5_version}")
                else:
                    # 文件已变化或首次添加，使用当前日期
                    md5_version = now.strftime('%Y%m%d')
                    if old_md5_version:
                        ColorPrint.warning(f"MD5 数据库已更新，版本号: {old_md5_version} → {md5_version}")
            
            manifest["resources"].append({
                "name": "md5",
                "displayName": "MD5密码库",
                "version": md5_version,
                "required": False,
                "description": "包含17亿条MD5密码数据，用于快速解密常见密码",
                "files": {
                    "url": {
                        "github": f"https://github.com/HotBoy-java/Resource/releases/download/MD5/{md5_db_filename}",
                        "mirror": f"{CONFIG['resource_mirror_base']}/{md5_db_filename}"
                    },
                    "size": gzip_size,  # 压缩文件的大小（下载大小）
                    "compressed": True,
                    "compressionType": "gzip",
                    "uncompressedSize": md5_db_info['size'],  # 解压后的大小
                    "checksum": {
                        # 使用解压后的文件计算校验和
                        "sha256": md5_db_info['sha256'],
                        "md5": md5_db_info['md5']
                    },
                    "localPath": "md5_database.db",
                    "minDiskSpace": md5_db_info['size'] + 200000000  # 基于解压后的大小
                }
            })
            ColorPrint.info(f"已添加 MD5 数据库资源: {md5_db_filename}")
            ColorPrint.info(f"  压缩文件大小: {gzip_size / 1024 / 1024:.2f} MB")
            ColorPrint.info(f"  解压后大小: {md5_db_info['size'] / 1024 / 1024:.2f} MB")
            ColorPrint.info(f"  校验和基于解压后的文件: {os.path.basename(db_path)}")
        
        # 添加 winKbInfo 资源
        if winkb_file_info:
            manifest["resources"].append({
                "name": "winKbInfo",
                "displayName": "Windows补丁信息库",
                "version": winkb_date if winkb_date else now.strftime('%Y%m%d'),
                "required": False,
                "description": "Windows系统安全补丁信息数据库，用于补丁查询",
                "files": {
                    "url": {
                        "github": f"https://raw.githubusercontent.com/HotBoy-java/Resource/main/{winkb_filename}",
                        "mirror": f"{CONFIG['resource_mirror_base']}/{winkb_filename}"
                    },
                    "size": winkb_file_info['size'],
                    "compressed": False,
                    "checksum": {
                        "sha256": winkb_file_info['sha256'],
                        "md5": winkb_file_info['md5']
                    },
                    "localPath": winkb_filename,
                    "minDiskSpace": winkb_file_info['size'] + 10000000
                }
            })
            ColorPrint.info(f"已添加 WinKbInfo 资源: {winkb_filename} (版本: {winkb_date})")
        
        # 保存 manifest.json
        with open(self.manifest_path, 'w', encoding='utf-8') as f:
            json.dump(manifest, f, indent=2, ensure_ascii=False)
        
        ColorPrint.success(f"manifest.json 生成完成")
        return self.manifest_path
    
    def find_md5_database(self):
        """查找 MD5 数据库文件（在 data 目录中）
        返回: (gzip_path, db_path) 或 None
        - gzip_path: 压缩文件路径（用于文件名和版本）
        - db_path: 解压后的文件路径（用于计算校验和）
        """
        if not os.path.exists(self.data_dir):
            return None
            
        pattern = r'md5_database.*\.db\.gzip'
        for filename in os.listdir(self.data_dir):
            if re.match(pattern, filename):
                gzip_path = os.path.join(self.data_dir, filename)
                # 获取对应的解压文件路径（去掉 .gzip 后缀）
                db_path = gzip_path.replace('.gzip', '')
                
                # 检查解压后的文件是否存在
                if os.path.exists(db_path):
                    return (gzip_path, db_path)
                else:
                    ColorPrint.warning(f"找到 {filename}，但未找到解压后的文件 {os.path.basename(db_path)}")
                    ColorPrint.warning("请先解压 gzip 文件，以便计算正确的校验和")
                    return None
        return None

class GitManager:
    """Git 管理器"""
    
    def __init__(self, project_dir):
        self.project_dir = project_dir
    
    def commit_and_push(self, files, commit_message):
        """提交并推送到 Git"""
        ColorPrint.process("正在提交到 Git...")
        
        try:
            os.chdir(self.project_dir)
            
            # 添加文件
            for file in files:
                subprocess.run(['git', 'add', file], check=True)
                ColorPrint.info(f"已添加: {file}")
            
            # 提交
            subprocess.run(['git', 'commit', '-m', commit_message], check=True)
            ColorPrint.success("提交成功")
            
            # 推送
            subprocess.run(['git', 'push', 'origin', 'main'], check=True)
            ColorPrint.success("推送到 GitHub 成功")
            
            return True
        except subprocess.CalledProcessError as e:
            ColorPrint.error(f"Git 操作失败: {str(e)}")
            return False

def print_summary(version, jar_info, winkb_info):
    """打印更新摘要"""
    print("\n" + "="*60)
    print("更新摘要".center(54))
    print("="*60)
    print(f"\n版本号: {version}")
    print(f"\nJAR 文件（从源目录读取）:")
    
    if 'jdk8' in jar_info:
        print(f"  - JDK8:  {jar_info['jdk8']['filename']}")
        print(f"    来源: {jar_info['jdk8']['path']}")
    else:
        print(f"  - JDK8:  (未找到)")
    
    if 'jdk11' in jar_info:
        print(f"  - JDK11: {jar_info['jdk11']['filename']}")
        print(f"    来源: {jar_info['jdk11']['path']}")
    else:
        print(f"  - JDK11: (未找到)")
    
    if winkb_info[0]:
        print(f"\nWinKbInfo（已保存到 data 目录）:")
        print(f"  - 文件: {os.path.basename(winkb_info[0])}")
        print(f"  - 版本: {winkb_info[1]}")
    
    print("\n" + "="*60 + "\n")

def main():
    """主函数"""
    print("\n" + "="*60)
    print("PotatoTool 自动化资源更新脚本".center(50))
    print("="*60 + "\n")
    
    try:
        # 1. 查找 JAR 文件（不复制）
        jar_manager = JarFileManager(CONFIG['jar_source_dir'])
        version, jdk8_jar, jdk11_jar = jar_manager.find_latest_jars()
        jar_info = jar_manager.get_jar_info(jdk8_jar, jdk11_jar)
        
        # 2. 更新 WinKbInfo（存储到 data 目录）
        winkb_updater = WinKbInfoUpdater(CONFIG['data_dir'])
        winkb_path, winkb_date = winkb_updater.update()
        
        # 3. 检查是否有变化（在生成 manifest.json 之前）
        manifest_generator = ManifestGenerator(CONFIG['project_dir'], CONFIG['data_dir'])
        has_changes, changes_list = manifest_generator.check_changes(version, jar_info, (winkb_path, winkb_date))
        
        if not has_changes:
            print("\n" + "="*60)
            ColorPrint.info("✓ 检测到资源无变化，无需更新")
            print("="*60)
            print(f"\n当前版本: {version}")
            print(f"JAR 文件: 无变化")
            print(f"WinKbInfo: 无变化")
            print(f"MD5 数据库: 无变化")
            print("\n" + "="*60 + "\n")
            ColorPrint.success("所有资源已是最新状态，无需重新生成和提交！")
            return
        
        # 4. 显示检测到的变化
        print("\n" + "="*60)
        ColorPrint.warning("检测到以下资源已更新:")
        print("="*60)
        for i, change in enumerate(changes_list, 1):
            print(f"  {i}. {change}")
        print("="*60 + "\n")
        
        # 5. 生成 manifest.json（保存到项目根目录）
        manifest_path = manifest_generator.generate(version, jar_info, (winkb_path, winkb_date))
        
        # 6. 打印摘要
        print_summary(version, jar_info, (winkb_path, winkb_date))
        
        # 7. 提交到 Git（只提交 manifest.json 和 data 目录下的资源文件）
        git_manager = GitManager(CONFIG['project_dir'])
        files_to_commit = ['manifest.json', 'data/']
        
        commit_message = f"Auto-update v{version} - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
        
        # 询问是否推送
        print("\n准备提交以下文件:")
        for f in files_to_commit:
            print(f"  - {f}")
        
        response = input("\n是否提交并推送到 GitHub? (y/n): ").strip().lower()
        
        if response == 'y':
            success = git_manager.commit_and_push(files_to_commit, commit_message)
            if success:
                ColorPrint.success("\n✓ 所有操作完成！")
            else:
                ColorPrint.warning("\n⚠ Git 操作失败，但文件已生成")
        else:
            ColorPrint.info("\n已跳过 Git 推送，文件已生成")
        
        # 提示关于 md5_database.db.gzip
        md5_db_result = manifest_generator.find_md5_database()
        if md5_db_result:
            gzip_path, db_path = md5_db_result
            print("\n" + "="*60)
            ColorPrint.warning("注意：md5_database.db.gzip 文件较大")
            ColorPrint.info(f"请手动上传到 GitHub Releases: {os.path.basename(gzip_path)}")
            ColorPrint.info("上传地址: https://github.com/HotBoy-java/Resource/releases")
            print("="*60)
        
    except Exception as e:
        ColorPrint.error(f"\n执行失败: {str(e)}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == '__main__':
    main()

