#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
GitHub Release 自动上传工具
用于上传大文件（如 md5_database.db.gzip）到 GitHub Releases
"""

import os
import sys
import json
import requests
import subprocess
from pathlib import Path

# 配置
CONFIG = {
    'owner': 'HotBoy-java',
    'repo': 'Resource',
    'release_tag': 'MD5',  # Release 标签
}

class ColorPrint:
    """彩色打印"""
    
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

class GitHubReleaseUploader:
    """GitHub Release 上传器"""
    
    def __init__(self, token=None):
        self.token = token or self._get_token()
        self.headers = {
            'Authorization': f'token {self.token}',
            'Accept': 'application/vnd.github.v3+json'
        }
        self.api_base = 'https://api.github.com'
    
    def _get_token(self):
        """获取 GitHub Token"""
        # 方法1: 从环境变量获取
        token = os.environ.get('GITHUB_TOKEN')
        if token:
            return token
        
        # 方法2: 从 git config 获取
        try:
            result = subprocess.run(
                ['git', 'config', '--get', 'github.token'],
                capture_output=True,
                text=True
            )
            if result.returncode == 0 and result.stdout.strip():
                return result.stdout.strip()
        except:
            pass
        
        # 方法3: 从文件读取
        token_file = os.path.expanduser('~/.github_token')
        if os.path.exists(token_file):
            with open(token_file, 'r') as f:
                return f.read().strip()
        
        return None
    
    def get_or_create_release(self, owner, repo, tag):
        """获取或创建 Release"""
        ColorPrint.process(f"检查 Release: {tag}")
        
        # 尝试获取已存在的 Release
        url = f"{self.api_base}/repos/{owner}/{repo}/releases/tags/{tag}"
        response = requests.get(url, headers=self.headers)
        
        if response.status_code == 200:
            ColorPrint.success(f"找到已存在的 Release: {tag}")
            return response.json()
        
        # 创建新 Release
        ColorPrint.process(f"创建新 Release: {tag}")
        url = f"{self.api_base}/repos/{owner}/{repo}/releases"
        data = {
            'tag_name': tag,
            'name': tag,
            'body': f'自动创建的 Release - {tag}',
            'draft': False,
            'prerelease': False
        }
        
        response = requests.post(url, headers=self.headers, json=data)
        
        if response.status_code == 201:
            ColorPrint.success(f"Release 创建成功: {tag}")
            return response.json()
        else:
            raise Exception(f"创建 Release 失败: {response.status_code} - {response.text}")
    
    def delete_asset_if_exists(self, owner, repo, release_id, filename):
        """删除已存在的同名资产"""
        # 获取 Release 的所有资产
        url = f"{self.api_base}/repos/{owner}/{repo}/releases/{release_id}/assets"
        response = requests.get(url, headers=self.headers)
        
        if response.status_code == 200:
            assets = response.json()
            for asset in assets:
                if asset['name'] == filename:
                    # 删除旧文件
                    ColorPrint.process(f"删除旧文件: {filename}")
                    delete_url = f"{self.api_base}/repos/{owner}/{repo}/releases/assets/{asset['id']}"
                    delete_response = requests.delete(delete_url, headers=self.headers)
                    
                    if delete_response.status_code == 204:
                        ColorPrint.success("旧文件删除成功")
                    else:
                        ColorPrint.warning(f"删除旧文件失败: {delete_response.status_code}")
    
    def upload_file(self, owner, repo, release_id, file_path):
        """上传文件到 Release"""
        filename = os.path.basename(file_path)
        file_size = os.path.getsize(file_path)
        
        ColorPrint.process(f"准备上传: {filename} ({file_size:,} 字节)")
        
        # 删除已存在的同名文件
        self.delete_asset_if_exists(owner, repo, release_id, filename)
        
        # 上传新文件
        upload_url = f"https://uploads.github.com/repos/{owner}/{repo}/releases/{release_id}/assets?name={filename}"
        
        headers = self.headers.copy()
        headers['Content-Type'] = 'application/octet-stream'
        
        # 对于大文件，显示上传进度
        ColorPrint.process("正在上传文件...")
        
        with open(file_path, 'rb') as f:
            response = requests.post(
                upload_url,
                headers=headers,
                data=f,
                timeout=3600  # 1小时超时
            )
        
        if response.status_code == 201:
            asset_info = response.json()
            ColorPrint.success(f"上传成功！")
            ColorPrint.info(f"  下载地址: {asset_info['browser_download_url']}")
            return asset_info
        else:
            raise Exception(f"上传失败: {response.status_code} - {response.text}")

class GitHubCLIUploader:
    """使用 GitHub CLI 上传"""
    
    @staticmethod
    def is_cli_available():
        """检查 gh CLI 是否可用"""
        try:
            result = subprocess.run(['gh', '--version'], capture_output=True)
            return result.returncode == 0
        except FileNotFoundError:
            return False
    
    @staticmethod
    def upload_file(owner, repo, tag, file_path):
        """使用 gh CLI 上传文件"""
        filename = os.path.basename(file_path)
        ColorPrint.process(f"使用 GitHub CLI 上传: {filename}")
        
        # 检查 Release 是否存在，不存在则创建
        check_cmd = f"gh release view {tag} --repo {owner}/{repo}"
        result = subprocess.run(check_cmd, shell=True, capture_output=True)
        
        if result.returncode != 0:
            ColorPrint.process(f"创建 Release: {tag}")
            create_cmd = f"gh release create {tag} --repo {owner}/{repo} --title '{tag}' --notes 'Auto-created release'"
            subprocess.run(create_cmd, shell=True, check=True)
        
        # 上传文件（会自动覆盖同名文件）
        upload_cmd = f"gh release upload {tag} '{file_path}' --repo {owner}/{repo} --clobber"
        result = subprocess.run(upload_cmd, shell=True, capture_output=True, text=True)
        
        if result.returncode == 0:
            ColorPrint.success("上传成功！")
            url = f"https://github.com/{owner}/{repo}/releases/tag/{tag}"
            ColorPrint.info(f"  Release 地址: {url}")
            return True
        else:
            raise Exception(f"上传失败: {result.stderr}")

def setup_github_token():
    """设置 GitHub Token"""
    print("\n" + "="*60)
    print("GitHub Token 设置向导".center(54))
    print("="*60 + "\n")
    
    ColorPrint.info("需要 GitHub Personal Access Token 来上传文件")
    ColorPrint.info("权限要求: repo (完整权限)")
    print()
    ColorPrint.info("获取 Token:")
    ColorPrint.info("  1. 访问: https://github.com/settings/tokens")
    ColorPrint.info("  2. 点击 'Generate new token (classic)'")
    ColorPrint.info("  3. 勾选 'repo' 权限")
    ColorPrint.info("  4. 生成并复制 token")
    print()
    
    token = input("请输入你的 GitHub Token: ").strip()
    
    if not token:
        ColorPrint.error("Token 不能为空")
        return None
    
    # 保存到文件
    token_file = os.path.expanduser('~/.github_token')
    with open(token_file, 'w') as f:
        f.write(token)
    os.chmod(token_file, 0o600)
    
    ColorPrint.success(f"Token 已保存到: {token_file}")
    
    # 也可以设置到 git config
    try:
        subprocess.run(['git', 'config', '--global', 'github.token', token], check=True)
        ColorPrint.success("Token 已添加到 git config")
    except:
        pass
    
    return token

def main():
    """主函数"""
    print("\n" + "="*60)
    print("GitHub Release 自动上传工具".center(52))
    print("="*60 + "\n")
    
    # 检查文件参数
    if len(sys.argv) < 2:
        ColorPrint.error("用法: python3 upload_to_release.py <文件路径>")
        print()
        print("示例:")
        print("  python3 upload_to_release.py md5_database_20250110.db.gzip")
        sys.exit(1)
    
    file_path = sys.argv[1]
    
    if not os.path.exists(file_path):
        ColorPrint.error(f"文件不存在: {file_path}")
        sys.exit(1)
    
    filename = os.path.basename(file_path)
    file_size = os.path.getsize(file_path)
    
    print(f"文件: {filename}")
    print(f"大小: {file_size:,} 字节 ({file_size / 1024 / 1024 / 1024:.2f} GB)")
    print(f"目标仓库: {CONFIG['owner']}/{CONFIG['repo']}")
    print(f"Release 标签: {CONFIG['release_tag']}")
    print()
    
    # 方法选择
    print("选择上传方法:")
    print("1) GitHub CLI (gh) - 推荐，速度快")
    print("2) GitHub API (需要 token)")
    print("0) 取消")
    print()
    
    choice = input("请选择 (0-2): ").strip()
    
    try:
        if choice == '1':
            # 使用 GitHub CLI
            if not GitHubCLIUploader.is_cli_available():
                ColorPrint.error("未安装 GitHub CLI")
                ColorPrint.info("安装方法:")
                ColorPrint.info("  macOS: brew install gh")
                ColorPrint.info("  其他: https://cli.github.com/")
                sys.exit(1)
            
            # 检查认证
            result = subprocess.run(['gh', 'auth', 'status'], capture_output=True)
            if result.returncode != 0:
                ColorPrint.warning("GitHub CLI 未认证")
                ColorPrint.info("运行: gh auth login")
                sys.exit(1)
            
            GitHubCLIUploader.upload_file(
                CONFIG['owner'],
                CONFIG['repo'],
                CONFIG['release_tag'],
                file_path
            )
            
        elif choice == '2':
            # 使用 GitHub API
            uploader = GitHubReleaseUploader()
            
            if not uploader.token:
                ColorPrint.warning("未找到 GitHub Token")
                token = setup_github_token()
                if not token:
                    sys.exit(1)
                uploader = GitHubReleaseUploader(token)
            
            # 获取或创建 Release
            release = uploader.get_or_create_release(
                CONFIG['owner'],
                CONFIG['repo'],
                CONFIG['release_tag']
            )
            
            # 上传文件
            uploader.upload_file(
                CONFIG['owner'],
                CONFIG['repo'],
                release['id'],
                file_path
            )
            
        elif choice == '0':
            ColorPrint.info("已取消")
            sys.exit(0)
        else:
            ColorPrint.error("无效的选项")
            sys.exit(1)
        
        print("\n" + "="*60)
        ColorPrint.success("✓ 上传完成！")
        print("="*60 + "\n")
        
    except Exception as e:
        ColorPrint.error(f"上传失败: {str(e)}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == '__main__':
    main()


