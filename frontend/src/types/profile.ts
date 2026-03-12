export type ProfileStatus = 'queued' | 'processing' | 'finished' | 'failed'

export interface AboutFieldEntity {
  id: string | null
  name: string | null
  url: string | null
  profile_url: string | null
  is_verified: boolean
  typename: string | null
}

export interface AboutField {
  text: string | null
  field_type: string | null
  entities: AboutFieldEntity[]
  details: string[]
  icon_url: string | null
}

export interface AboutSection {
  section_type: string | null
  title: string | null
  fields: AboutField[]
}

export interface AboutTab {
  name: string | null
  url: string | null
  sections: AboutSection[]
}

export interface WorkItem {
  organization: string | null
  designation: string | null
  details: string[]
}

export interface EducationItem {
  institution: string | null
  type: string | null
  field_of_study: string | null
  details: string[]
}

export interface LocationInfo {
  upazila: string | null
  district: string | null
  division: string | null
  country: string | null
}

export interface BirthdayInfo {
  birthday: string | null
  birthdate: string | null
  birth_year: string | null
}

export interface PartnerInfo {
  name: string | null
  profile_url: string | null
}

export interface RelationshipItem {
  status: string | null
  partner_info: PartnerInfo | null
  details: string[]
}

export interface FamilyMember {
  name: string | null
  relationship: string | null
  profile_url: string | null
}

export interface NamesInfo {
  nicknames: string[]
  name_pronunciation: string | null
}

export interface ProfileData {
  profile_id: string | null
  name: string | null
  profile_url: string | null
  profile_picture_url: string | null
  profile_picture_path: string | null
  cover_photo_url: string | null
  cover_photo_path: string | null
  bio: string | null
  category: string | null
  followers_count: number | null
  friends_count: number | null
  work: WorkItem[]
  education: EducationItem[]
  current_city: LocationInfo | null
  hometown: LocationInfo | null
  birthday_info: BirthdayInfo | null
  relationship: RelationshipItem[]
  family_members: FamilyMember[]
  gender: string | null
  language_skills: string[]
  names: NamesInfo | null
  intro_items: string[]
  scraped_at: string | null
}

export interface ScrapedDataRef {
  about_tabs: AboutTab[]
}

export interface ProfileDocument {
  id: string
  url: string
  url_slug: string
  status: ProfileStatus
  error_message: string | null
  created_at: string
  updated_at: string
  scraped_at: string | null
  profile: ProfileData | null
  scraped_data: ScrapedDataRef | null
}

export interface ProfileListResponse {
  items: ProfileDocument[]
  total: number
  page: number
  pages: number
}

export interface QueueStatusResponse {
  queued: number
  processing: number
  finished: number
  failed: number
}

export interface QueueUpdateEvent {
  event: 'status_change'
  data: {
    id: string
    url: string
    status: ProfileStatus
    name: string | null
    updated_at: string
  }
}
