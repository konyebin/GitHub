import unittest
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from rules import (
    graduation_term,
    linkedin_search_url,
    primary_skill,
    score_formulas,
    score_key,
    skill_formulas,
    skill_tags,
    status_key,
)


class RuleTests(unittest.TestCase):
    def test_former_intern_does_not_also_count_as_experience(self):
        self.assertEqual(skill_tags("Former Intern"), ["Former Intern"])
        self.assertEqual(primary_skill("Former Intern"), "Former Intern")

    def test_studying_wins_over_certification_mention(self):
        tags = skill_tags("Studying for CCNA")
        self.assertEqual(tags, ["Studying", "Certification"])
        self.assertEqual(primary_skill("Studying for CCNA"), "Studying")

    def test_misspelled_practitioner_is_a_certification(self):
        self.assertEqual(primary_skill("AWS Cloud Practioner"), "Certification")

    def test_degree(self):
        self.assertEqual(primary_skill("B.S. in Computer Engineering"), "Degree")

    def test_na(self):
        self.assertEqual(skill_tags("N/A"), ["N/A"])
        self.assertEqual(skill_tags("  NA "), ["N/A"])

    def test_blank_skill(self):
        self.assertEqual(skill_tags(None), [])
        self.assertIsNone(primary_skill("   "))

    def test_status_trims_and_distinguishes_sent_from_confirmed(self):
        confirmed = "Sent Assessment Center Instructions and Candidate Confirmed Availability "
        sent = "Sent Assessment Center Instructions"
        self.assertEqual(status_key(confirmed), "Confirmed")
        self.assertEqual(status_key(sent), "Sent")
        self.assertEqual(status_key("Not interested in the role"), "Not interested")
        self.assertEqual(status_key(""), "Blank")
        self.assertEqual(status_key(None), "Blank")

    def test_graduation_terms_group_abbreviations(self):
        self.assertEqual(graduation_term("December 2026"), "Dec 2026")
        self.assertEqual(graduation_term("Dec 2026"), "Dec 2026")
        self.assertEqual(graduation_term("Aug 2026"), "Aug 2026")
        self.assertEqual(graduation_term("August 2026"), "Aug 2026")

    def test_score_bands(self):
        self.assertEqual(score_key(24), "Passing")
        self.assertEqual(score_key("26"), "Passing")
        self.assertEqual(score_key(23), "NearPass")
        self.assertEqual(score_key("22"), "NearPass")
        self.assertEqual(score_key(21), "NearPass")
        self.assertEqual(score_key(20), "Below")
        self.assertEqual(score_key("0"), "Below")
        self.assertEqual(score_key("N/A"), "N/A")
        self.assertEqual(score_key(" NA "), "N/A")
        self.assertEqual(score_key(""), "Blank")
        self.assertEqual(score_key(None), "Blank")

    def test_linkedin_search_uses_name_and_city(self):
        url = linkedin_search_url("Ada Lovelace", "London")
        self.assertTrue(url.startswith("https://www.linkedin.com/search/results/people/?keywords="))
        self.assertIn("Ada%20Lovelace", url)
        self.assertIn("London", url)
        self.assertEqual(linkedin_search_url("", "  "), "")

    def test_score_formulas_check_na_before_passing(self):
        keys = [key for key, _formula in score_formulas("I2")]
        self.assertEqual(keys, ["N/A", "NearPass", "Passing"])

    def test_sheet_formulas_follow_priority(self):
        keys = [key for key, _formula in skill_formulas("D2")]
        self.assertEqual(
            keys,
            ["Former Intern", "Studying", "Certification", "Degree", "Experience", "N/A"],
        )


if __name__ == "__main__":
    unittest.main()
