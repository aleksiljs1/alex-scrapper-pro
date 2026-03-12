// MongoDB initialization script
// Creates indexes for the profiles collection

db = db.getSiblingDB('facebook_scraper');

db.profiles.createIndex({ "url": 1 }, { unique: true });
db.profiles.createIndex({ "url_slug": 1 });
db.profiles.createIndex({ "status": 1 });
db.profiles.createIndex({ "created_at": -1 });

// Location indexes (current_city + hometown)
db.profiles.createIndex({ "profile.current_city.district": 1 });
db.profiles.createIndex({ "profile.current_city.division": 1 });
db.profiles.createIndex({ "profile.current_city.upazila": 1 });
db.profiles.createIndex({ "profile.current_city.country": 1 });
db.profiles.createIndex({ "profile.hometown.district": 1 });
db.profiles.createIndex({ "profile.hometown.division": 1 });

// Education index
db.profiles.createIndex({ "profile.education.institution": 1, "profile.education.type": 1 });

// Wildcard text index for keyword search across all profile text fields
db.profiles.createIndex(
  {
    "profile.name": "text",
    "url": "text",
    "profile.bio": "text",
    "profile.category": "text",
    "profile.work.organization": "text",
    "profile.work.designation": "text",
    "profile.education.institution": "text",
    "profile.intro_items": "text",
  },
  { name: "profile_text_search" }
);

print("✅ MongoDB indexes created for facebook_scraper.profiles");
