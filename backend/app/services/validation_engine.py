import difflib
import logging
from typing import List, Tuple
from app.schemas.canonical import (
    CanonicalConversation, MinutesOfMeeting, ActionItem, Decision,
    Risk, Participant, ActionStatus, ApprovalMode
)

logger = logging.getLogger(__name__)

class ValidationEngine:
    """
    Enterprise guardrail preventing hallucinations and unverified actions from executing.
    Validates evidence quotations against ground-truth transcript and checks owner identities.
    """

    @staticmethod
    def verify_evidence_in_transcript(evidence_quote: str, full_transcript_text: str) -> bool:
        """Checks if the evidence quote exists in the spoken transcript with fuzzy tolerance."""
        if not evidence_quote or not full_transcript_text:
            return False

        quote_clean = evidence_quote.lower().strip()
        transcript_clean = full_transcript_text.lower().strip()

        # Direct containment check
        if quote_clean in transcript_clean:
            return True

        # Fuzzy matching for slight ASR variation
        words = quote_clean.split()
        if len(words) < 3:
            return False

        sample = " ".join(words[:min(6, len(words))])
        return sample in transcript_clean

    @classmethod
    def validate_action_items(
        cls,
        actions: List[ActionItem],
        participants: List[Participant],
        transcript_text: str,
        approval_mode: ApprovalMode
    ) -> List[ActionItem]:
        """Validates actions for evidence, resolves participant identities, and sets lifecycle status."""
        participant_map = {p.name.lower(): p for p in participants}

        validated_actions = []
        for action in actions:
            # 1. Evidence Verification
            has_evidence = cls.verify_evidence_in_transcript(action.evidence, transcript_text)
            if not has_evidence:
                action.validation_status = "EVIDENCE_UNVERIFIED"
                action.confidence = min(action.confidence, 0.5)
            else:
                action.validation_status = "VERIFIED"

            # 2. Identity Resolution
            matched_p = None
            owner_lower = action.owner.lower()
            for p_name_lower, p_obj in participant_map.items():
                if owner_lower in p_name_lower or p_name_lower in owner_lower:
                    matched_p = p_obj
                    break

            if matched_p:
                action.owner = matched_p.name
                action.owner_email = matched_p.email
            else:
                action.validation_status = f"{action.validation_status}_UNRESOLVED_OWNER"

            # 3. Policy & Approval Gate
            if approval_mode == ApprovalMode.AUTO_CONFIDENCE:
                if action.confidence >= 0.90 and has_evidence and matched_p:
                    action.status = ActionStatus.APPROVED
                else:
                    action.status = ActionStatus.PROPOSED
            else:
                # Mode A: Always requires manual human approval
                action.status = ActionStatus.PROPOSED

            validated_actions.append(action)

        return validated_actions

    @classmethod
    def validate_mom(
        cls,
        mom: MinutesOfMeeting,
        participants: List[Participant],
        transcript_text: str,
        approval_mode: ApprovalMode = ApprovalMode.MANUAL_APPROVAL
    ) -> MinutesOfMeeting:
        """Applies comprehensive validation to entire MoM package."""
        mom.action_items = cls.validate_action_items(
            mom.action_items,
            participants,
            transcript_text,
            approval_mode
        )
        return mom

validation_engine = ValidationEngine()
