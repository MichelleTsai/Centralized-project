#!/usr/bin/env python3
import requests
import os
import sys
from typing import List, Dict

class MilestonesAndIssuesMigrator:
    def __init__(self, github_token):
        self.token = github_token
        self.headers = {
            "Authorization": f"token {github_token}",
            "Accept": "application/vnd.github.v3+json"
        }
        self.base_url = "https://api.github.com"
        self.milestone_mapping = {}  # Maps old milestone numbers to new ones

    def get_milestones(self, owner, repo):
        """Fetch all milestones from a repository"""
        url = f"{self.base_url}/repos/{owner}/{repo}/milestones"
        milestones = []
        page = 1
        
        print(f"📊 Fetching milestones from {owner}/{repo}...")
        while True:
            params = {"state": "all", "per_page": 100, "page": page}
            response = requests.get(url, headers=self.headers, params=params)
            
            if response.status_code != 200:
                print(f"❌ Error fetching milestones: {response.status_code}")
                print(response.json())
                sys.exit(1)
            
            data = response.json()
            if not data:
                break
            
            milestones.extend(data)
            page += 1
        
        return milestones

    def create_milestone(self, owner, repo, milestone):
        """Create a milestone in the target repository"""
        url = f"{self.base_url}/repos/{owner}/{repo}/milestones"
        
        payload = {
            "title": milestone["title"],
            "description": milestone.get("description", ""),
            "due_on": milestone.get("due_on")
        }
        
        # Remove None values
        payload = {k: v for k, v in payload.items() if v is not None}
        
        response = requests.post(url, headers=self.headers, json=payload)
        
        if response.status_code == 201:
            new_milestone = response.json()
            self.milestone_mapping[milestone["number"]] = new_milestone["number"]
            print(f"✅ Created milestone: {milestone['title']} (ID: {new_milestone['number']})")
            return new_milestone
        elif response.status_code == 422:
            print(f"⚠️  Milestone already exists: {milestone['title']}")
            # Try to find the existing milestone
            existing = self.get_milestone_by_title(owner, repo, milestone['title'])
            if existing:
                self.milestone_mapping[milestone["number"]] = existing["number"]
                return existing
            return None
        else:
            print(f"❌ Error creating milestone '{milestone['title']}': {response.status_code}")
            print(response.json())
            return None

    def get_milestone_by_title(self, owner, repo, title):
        """Find an existing milestone by title"""
        url = f"{self.base_url}/repos/{owner}/{repo}/milestones"
        params = {"state": "all", "per_page": 100}
        response = requests.get(url, headers=self.headers, params=params)
        
        if response.status_code == 200:
            for milestone in response.json():
                if milestone["title"] == title:
                    return milestone
        return None

    def get_issues_by_milestone(self, owner, repo, milestone_number):
        """Fetch all issues associated with a milestone"""
        url = f"{self.base_url}/repos/{owner}/{repo}/issues"
        issues = []
        page = 1
        
        while True:
            params = {
                "milestone": milestone_number,
                "state": "all",
                "per_page": 100,
                "page": page
            }
            response = requests.get(url, headers=self.headers, params=params)
            
            if response.status_code != 200:
                print(f"❌ Error fetching issues: {response.status_code}")
                return []
            
            data = response.json()
            if not data:
                break
            
            issues.extend(data)
            page += 1
        
        return issues

    def create_issue(self, owner, repo, issue, new_milestone_number=None):
        """Create an issue in the target repository"""
        url = f"{self.base_url}/repos/{owner}/{repo}/issues"
        
        payload = {
            "title": issue["title"],
            "body": issue.get("body", ""),
            "labels": [label["name"] for label in issue.get("labels", [])],
            "milestone": new_milestone_number
        }
        
        # Remove None values
        payload = {k: v for k, v in payload.items() if v is not None}
        
        response = requests.post(url, headers=self.headers, json=payload)
        
        if response.status_code == 201:
            new_issue = response.json()
            print(f"  ✅ Created issue: {issue['title']} (#{new_issue['number']})")
            return new_issue
        else:
            print(f"  ❌ Error creating issue '{issue['title']}': {response.status_code}")
            if response.status_code != 422:
                print(f"     {response.json()}")
            return None

    def migrate(self, source_owner, source_repo, target_owner, target_repo):
        """Migrate milestones and associated issues"""
        print(f"\n{'='*60}")
        print(f"🚀 Starting Migration")
        print(f"{'='*60}\n")
        
        # Step 1: Get and create milestones
        milestones = self.get_milestones(source_owner, source_repo)
        
        if not milestones:
            print("⚠️  No milestones found in source repository")
            return
        
        print(f"📊 Found {len(milestones)} milestone(s)\n")
        print("📤 Creating milestones in target repository...\n")
        
        created_milestones = 0
        for milestone in milestones:
            if self.create_milestone(target_owner, target_repo, milestone):
                created_milestones += 1
        
        print(f"\n✅ Milestones created: {created_milestones}\n")
        
        # Step 2: Get and create issues associated with milestones
        print(f"{'='*60}")
        print("📝 Migrating Issues")
        print(f"{'='*60}\n")
        
        total_issues = 0
        created_issues = 0
        
        for milestone in milestones:
            milestone_number = milestone["number"]
            milestone_title = milestone["title"]
            
            issues = self.get_issues_by_milestone(source_owner, source_repo, milestone_number)
            
            if issues:
                print(f"📋 Milestone: {milestone_title} ({len(issues)} issues)")
                
                # Get the new milestone number from mapping
                new_milestone_number = self.milestone_mapping.get(milestone_number)
                
                for issue in issues:
                    total_issues += 1
                    if self.create_issue(target_owner, target_repo, issue, new_milestone_number):
                        created_issues += 1
                
                print()
        
        # Summary
        print(f"{'='*60}")
        print("✅ Migration Summary")
        print(f"{'='*60}")
        print(f"Milestones created: {created_milestones}")
        print(f"Issues created: {created_issues}/{total_issues}")
        print(f"{'='*60}\n")

def main():
    github_token = os.getenv("GITHUB_TOKEN")
    source_owner = os.getenv("SOURCE_OWNER")
    source_repo = os.getenv("SOURCE_REPO")
    target_owner = os.getenv("TARGET_OWNER")
    target_repo = os.getenv("TARGET_REPO")
    
    if not all([github_token, source_owner, source_repo, target_owner, target_repo]):
        print("❌ Missing required environment variables")
        sys.exit(1)
    
    migrator = MilestonesAndIssuesMigrator(github_token)
    migrator.migrate(source_owner, source_repo, target_owner, target_repo)

if __name__ == "__main__":
    main()
