#!/usr/bin/env python3
import requests
import os
import sys
from typing import List, Dict

class MilestonesAndIssuesSync:
    def __init__(self, github_token):
        self.token = github_token
        self.headers = {
            "Authorization": f"token {github_token}",
            "Accept": "application/vnd.github.v3+json"
        }
        self.base_url = "https://api.github.com"
        self.issue_mapping = {}  # Maps source issue numbers to target issue numbers

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
                sys.exit(1)
            
            data = response.json()
            if not data:
                break
            
            milestones.extend(data)
            page += 1
        
        return milestones

    def sync_milestone(self, owner, repo, milestone, target_owner, target_repo, milestone_mapping):
        """Create or update milestone in target repo"""
        url = f"{self.base_url}/repos/{target_owner}/{target_repo}/milestones"
        
        payload = {
            "title": milestone["title"],
            "description": milestone.get("description", ""),
            "due_on": milestone.get("due_on"),
            "state": milestone.get("state", "open")
        }
        
        # Remove None values
        payload = {k: v for k, v in payload.items() if v is not None}
        
        # Check if milestone already exists
        existing = self.get_milestone_by_title(target_owner, target_repo, milestone["title"])
        
        if existing:
            # Update existing milestone
            update_url = f"{url}/{existing['number']}"
            response = requests.patch(update_url, headers=self.headers, json=payload)
            
            if response.status_code == 200:
                new_milestone = response.json()
                milestone_mapping[milestone["number"]] = new_milestone["number"]
                print(f"✅ Synced milestone: {milestone['title']} (ID: {new_milestone['number']})")
                return new_milestone
            else:
                print(f"❌ Error syncing milestone '{milestone['title']}': {response.status_code}")
                return None
        else:
            # Create new milestone
            response = requests.post(url, headers=self.headers, json=payload)
            
            if response.status_code == 201:
                new_milestone = response.json()
                milestone_mapping[milestone["number"]] = new_milestone["number"]
                print(f"✅ Created milestone: {milestone['title']} (ID: {new_milestone['number']})")
                return new_milestone
            else:
                print(f"❌ Error creating milestone '{milestone['title']}': {response.status_code}")
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

    def sync_issue(self, owner, repo, issue, target_owner, target_repo, new_milestone_number=None):
        """Create or update issue in target repository"""
        url = f"{self.base_url}/repos/{target_owner}/{target_repo}/issues"
        
        payload = {
            "title": issue["title"],
            "body": issue.get("body", ""),
            "labels": [label["name"] for label in issue.get("labels", [])],
            "milestone": new_milestone_number,
            "state": issue.get("state", "open")
        }
        
        # Remove None values
        payload = {k: v for k, v in payload.items() if v is not None}
        
        # Check if issue already exists by title
        existing = self.get_issue_by_title(target_owner, target_repo, issue["title"])
        
        if existing:
            # Update existing issue
            update_url = f"{self.base_url}/repos/{target_owner}/{target_repo}/issues/{existing['number']}"
            response = requests.patch(update_url, headers=self.headers, json=payload)
            
            if response.status_code == 200:
                new_issue = response.json()
                self.issue_mapping[issue["number"]] = new_issue["number"]
                print(f"  ✅ Synced issue: {issue['title']} (#{new_issue['number']})")
                return new_issue
            else:
                print(f"  ❌ Error syncing issue '{issue['title']}': {response.status_code}")
                return None
        else:
            # Create new issue
            response = requests.post(url, headers=self.headers, json=payload)
            
            if response.status_code == 201:
                new_issue = response.json()
                self.issue_mapping[issue["number"]] = new_issue["number"]
                print(f"  ✅ Created issue: {issue['title']} (#{new_issue['number']})")
                return new_issue
            else:
                print(f"  ❌ Error creating issue '{issue['title']}': {response.status_code}")
                return None

    def get_issue_by_title(self, owner, repo, title):
        """Find an existing issue by title"""
        url = f"{self.base_url}/repos/{owner}/{repo}/issues"
        params = {"state": "all", "per_page": 100}
        response = requests.get(url, headers=self.headers, params=params)
        
        if response.status_code == 200:
            for issue in response.json():
                if issue["title"] == title:
                    return issue
        return None

    def sync_bidirectional(self, source_owner, source_repo, target_owner, target_repo):
        """Sync milestones and issues bidirectionally"""
        print(f"\n{'='*60}")
        print(f"🔄 Starting Bi-directional Sync")
        print(f"{'='*60}\n")
        
        milestone_mapping = {}
        
        # Step 1: Get and sync milestones from source to target
        print("📤 Syncing milestones from SOURCE to TARGET...\n")
        source_milestones = self.get_milestones(source_owner, source_repo)
        
        if not source_milestones:
            print("⚠️  No milestones found in source repository")
            return
        
        print(f"📊 Found {len(source_milestones)} milestone(s)\n")
        
        synced_milestones = 0
        for milestone in source_milestones:
            if self.sync_milestone(source_owner, source_repo, milestone, target_owner, target_repo, milestone_mapping):
                synced_milestones += 1
        
        print(f"\n✅ Milestones synced: {synced_milestones}\n")
        
        # Step 2: Sync issues associated with milestones
        print(f"{'='*60}")
        print("📝 Syncing Issues")
        print(f"{'='*60}\n")
        
        total_issues = 0
        synced_issues = 0
        
        for milestone in source_milestones:
            milestone_number = milestone["number"]
            milestone_title = milestone["title"]
            
            issues = self.get_issues_by_milestone(source_owner, source_repo, milestone_number)
            
            if issues:
                print(f"📋 Milestone: {milestone_title} ({len(issues)} issues)")
                
                # Get the new milestone number from mapping
                new_milestone_number = milestone_mapping.get(milestone_number)
                
                for issue in issues:
                    total_issues += 1
                    if self.sync_issue(source_owner, source_repo, issue, target_owner, target_repo, new_milestone_number):
                        synced_issues += 1
                
                print()
        
        # Step 3: Create mapping file for reverse sync
        self.save_mappings(source_owner, source_repo, target_owner, target_repo)
        
        # Summary
        print(f"{'='*60}")
        print("✅ Sync Summary")
        print(f"{'='*60}")
        print(f"Milestones synced: {synced_milestones}")
        print(f"Issues synced: {synced_issues}/{total_issues}")
        print(f"\n📌 Note: Changes made to issues in {target_owner}/{target_repo}")
        print(f"   can be synced back to {source_owner}/{source_repo}")
        print(f"{'='*60}\n")

    def save_mappings(self, source_owner, source_repo, target_owner, target_repo):
        """Save issue mappings for reverse sync"""
        mapping_data = {
            "source": f"{source_owner}/{source_repo}",
            "target": f"{target_owner}/{target_repo}",
            "issue_mappings": self.issue_mapping
        }
        
        # Save to a file in the repository
        import json
        with open(".github/issue-mappings.json", "w") as f:
            json.dump(mapping_data, f, indent=2)
        
        print("📝 Issue mappings saved to .github/issue-mappings.json")

def main():
    github_token = os.getenv("GITHUB_TOKEN")
    source_owner = os.getenv("SOURCE_OWNER")
    source_repo = os.getenv("SOURCE_REPO")
    target_owner = os.getenv("TARGET_OWNER")
    target_repo = os.getenv("TARGET_REPO")
    
    if not all([github_token, source_owner, source_repo, target_owner, target_repo]):
        print("❌ Missing required environment variables")
        sys.exit(1)
    
    syncer = MilestonesAndIssuesSync(github_token)
    syncer.sync_bidirectional(source_owner, source_repo, target_owner, target_repo)

if __name__ == "__main__":
    main()
