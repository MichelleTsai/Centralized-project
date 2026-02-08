#!/usr/bin/env python3
import requests
import os
import sys

class MilestonesMigrator:
    def __init__(self, github_token):
        self.token = github_token
        self.headers = {
            "Authorization": f"token {github_token}",
            "Accept": "application/vnd.github.v3+json"
        }
        self.base_url = "https://api.github.com"

    def get_milestones(self, owner, repo):
        """Fetch all milestones from a repository"""
        url = f"{self.base_url}/repos/{owner}/{repo}/milestones"
        milestones = []
        page = 1
        
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
            print(f"✅ Created milestone: {milestone['title']}")
            return True
        elif response.status_code == 422:
            print(f"⚠️  Milestone already exists: {milestone['title']}")
            return False
        else:
            print(f"❌ Error creating milestone '{milestone['title']}': {response.status_code}")
            print(response.json())
            return False

    def migrate(self, source_owner, source_repo, target_owner, target_repo):
        """Migrate all milestones from source to target repository"""
        print(f"🔄 Fetching milestones from {source_owner}/{source_repo}...")
        milestones = self.get_milestones(source_owner, source_repo)
        
        if not milestones:
            print("⚠️  No milestones found in source repository")
            return
        
        print(f"📊 Found {len(milestones)} milestone(s)")
        print(f"📤 Migrating to {target_owner}/{target_repo}...\n")
        
        created_count = 0
        for milestone in milestones:
            if self.create_milestone(target_owner, target_repo, milestone):
                created_count += 1
        
        print(f"\n✅ Migration complete: {created_count} milestone(s) created")

def main():
    github_token = os.getenv("GITHUB_TOKEN")
    source_owner = os.getenv("SOURCE_OWNER")
    source_repo = os.getenv("SOURCE_REPO")
    target_owner = os.getenv("TARGET_OWNER")
    target_repo = os.getenv("TARGET_REPO")
    
    if not all([github_token, source_owner, source_repo, target_owner, target_repo]):
        print("❌ Missing required environment variables")
        sys.exit(1)
    
    migrator = MilestonesMigrator(github_token)
    migrator.migrate(source_owner, source_repo, target_owner, target_repo)

if __name__ == "__main__":
    main()
