from typing import cast, Literal
from functools import reduce
import operator

from ...payloads.models import (
    MessageLinkMappingModel,
    MessageMappingModel,
    ChannelPermissionsMappingModel,
    TwoFactorActionMappingModel,
    PollMappingModel,
    PollStateMappingModel,
    PollResultMappingModel,
    PollVoteMappingModel,
    PrivacyAccessMappingModel,
    PrivacySettingsMappingModel,
)
from ...payloads.shared import PollAnswerMappingModel, PollFlagsMappingModel
from ......models import (
    Message,
    ChannelPermissions,
    TwoFactorAction,
    PollFlags,
    Poll,
    PollAnswer,
    PollState,
    PollVote,
    PollResult,
    PrivacyAccess,
    PrivacySettings,
)


def reverse_translate_message(message: Message) -> MessageMappingModel | None:
    """Reverse translate message.

    :param message: Message instance to process.
    :type message: Message
    :returns: The resulting MessageMappingModel | None value.
    :rtype: MessageMappingModel | None
    :raises RuntimeError: If in message link exists, but not bound to another message.
    """
    if not message:
        return None
    message_link = message.link
    if message.status not in ("USER", "EDITED", "REPLY"):
        status = "USER"
    else:
        status = message.status
    if message_link:
        inner_message = message_link.message

        if inner_message is None:
            raise RuntimeError(
                "In message link exists, but not bound to another message"
            )
        msg = MessageMappingModel(
            id=message.message_id,
            status=cast(Literal["USER", "EDITED", "REPLY"], status),
            time=message.time,
            type=message.type,
            text=message.text if message.text else None,
            elements=message.elements if message.elements and message.text else None,
            chat_id=message.chat_id,
            link=MessageLinkMappingModel(
                type=message_link.type,
                message=reverse_translate_message(inner_message),
            ),
        )
        msg.attaches = message.attaches
        return msg

    msg = MessageMappingModel(
        id=message.message_id,
        status=cast(Literal["USER", "EDITED", "REPLY"], status),
        time=message.time,
        type=message.type,
        text=message.text if message.text else None,
        elements=message.elements if message.elements and message.text else None,
        chat_id=message.chat_id,
    )
    msg.attaches = message.attaches
    return msg


channel_permissions_map: dict[ChannelPermissions, ChannelPermissionsMappingModel] = {
    ChannelPermissions.ADD_REMOVE_MEMBER: ChannelPermissionsMappingModel.ADD_REMOVE_MEMBER,
    ChannelPermissions.ADD_ADMIN: ChannelPermissionsMappingModel.ADD_ADMIN,
    ChannelPermissions.CHANGE_CHAT_INFO: ChannelPermissionsMappingModel.CHANGE_CHAT_INFO,
    ChannelPermissions.PIN_MESSAGE: ChannelPermissionsMappingModel.PIN_MESSAGE,
    ChannelPermissions.POST_MESSAGE: ChannelPermissionsMappingModel.POST_MESSAGE,
    ChannelPermissions.EDIT_MESSAGE: ChannelPermissionsMappingModel.EDIT_MESSAGE,
    ChannelPermissions.DELETE_MESSAGE: ChannelPermissionsMappingModel.DELETE_MESSAGE,
}


def reverse_translate_channel_permissions(
    channel_permission: ChannelPermissions,
) -> ChannelPermissionsMappingModel:
    """Reverse translate channel permissions.

    :param channel_permission: ChannelPermissions instance to process.
    :type channel_permission: ChannelPermissions
    :returns: The resulting ChannelPermissionsMappingModel value.
    :rtype: ChannelPermissionsMappingModel
    """
    return channel_permissions_map[channel_permission]


two_factor_action_map: dict[TwoFactorAction, TwoFactorActionMappingModel] = {
    TwoFactorAction.SET_PASSWORD: TwoFactorActionMappingModel.SET_PASSWORD,
    TwoFactorAction.HINT: TwoFactorActionMappingModel.HINT,
    TwoFactorAction.EMAIL: TwoFactorActionMappingModel.EMAIL,
    TwoFactorAction.UPDATE_PASSWORD: TwoFactorActionMappingModel.UPDATE_PASSWORD,
    TwoFactorAction.REMOVE_2FA: TwoFactorActionMappingModel.REMOVE_2FA,
    TwoFactorAction.RESTORE_PASSWORD: TwoFactorActionMappingModel.RESTORE_PASSWORD,
}


def reverse_translate_two_factor_actions(
    two_factor_action: TwoFactorAction,
) -> TwoFactorActionMappingModel:
    """Reverse translate two factor actions.

    :param two_factor_action: TwoFactorAction instance to process.
    :type two_factor_action: TwoFactorAction
    :returns: The resulting TwoFactorActionMappingModel value.
    :rtype: TwoFactorActionMappingModel
    """
    return two_factor_action_map[two_factor_action]


poll_flags_map: dict[PollFlags, PollFlagsMappingModel] = {
    PollFlags.FLAG_SETTINGS_QUIZ: PollFlagsMappingModel.FLAG_SETTINGS_QUIZ,
    PollFlags.FLAG_SETTINGS_CLOSED: PollFlagsMappingModel.FLAG_SETTINGS_CLOSED,
    PollFlags.FLAG_SETTINGS_REVOTE: PollFlagsMappingModel.FLAG_SETTINGS_REVOTE,
    PollFlags.FLAG_SETTINGS_MULTISELECT: PollFlagsMappingModel.FLAG_SETTINGS_MULTISELECT,
    PollFlags.FLAG_SETTINGS_CAN_FORWARD: PollFlagsMappingModel.FLAG_SETTINGS_CAN_FORWARD,
    PollFlags.FLAG_SETTINGS_ANONYMOUS: PollFlagsMappingModel.FLAG_SETTINGS_ANONYMOUS,
}


def reverse_translate_poll_flags(
    poll_flags: PollFlags,
) -> PollFlagsMappingModel:
    """Reverse translate poll flags.

    :param poll_flags: PollFlags instance to process.
    :type poll_flags: PollFlags
    :returns: The resulting PollFlagsMappingModel value.
    :rtype: PollFlagsMappingModel
    """
    flags = [poll_flags_map[poll_flag] for poll_flag in poll_flags]

    if not flags:
        return PollFlagsMappingModel(0)

    return reduce(operator.or_, flags)


def reverse_translate_poll_vote(
    poll_vote: PollVote,
) -> PollVoteMappingModel:
    """Reverse translate poll vote.

    :param poll_vote: PollVote instance to process.
    :type poll_vote: PollVote
    :returns: The resulting PollVoteMappingModel value.
    :rtype: PollVoteMappingModel
    """
    return PollVoteMappingModel(
        timestamp=poll_vote.timestamp,
        user_id=poll_vote.user_id,
    )


def reverse_translate_poll_result(
    poll_result: PollResult,
) -> PollResultMappingModel:
    """Reverse translate poll result.

    :param poll_result: PollResult instance to process.
    :type poll_result: PollResult
    :returns: The resulting PollResultMappingModel value.
    :rtype: PollResultMappingModel
    """
    return PollResultMappingModel(
        answer_id=poll_result.answer_id,
        vote_count=poll_result.vote_count,
        rate=poll_result.rate,
        options=poll_result.options,
        votes=[reverse_translate_poll_vote(vote) for vote in poll_result.votes],
    )


def reverse_translate_poll_state(
    poll_state: PollState,
) -> PollStateMappingModel:
    """Reverse translate poll state.

    :param poll_state: PollState instance to process.
    :type poll_state: PollState
    :returns: The resulting PollStateMappingModel value.
    :rtype: PollStateMappingModel
    """
    return PollStateMappingModel(
        total=poll_state.total,
        voter_preview_ids=poll_state.voter_preview_ids,
        result=(
            [reverse_translate_poll_result(res) for res in poll_state.result]
            if poll_state.result is not None
            else None
        ),
    )


def reverse_translate_poll_answer(
    poll_answer: PollAnswer,
) -> PollAnswerMappingModel:
    """Reverse translate poll answer.

    :param poll_answer: PollAnswer instance to process.
    :type poll_answer: PollAnswer
    :returns: The resulting PollAnswerMappingModel value.
    :rtype: PollAnswerMappingModel
    """
    return PollAnswerMappingModel(
        text=poll_answer.text,
        answer_id=poll_answer.answer_id,
    )


def reverse_translate_poll(
    poll: Poll,
) -> PollMappingModel:
    """Reverse translate poll.

    :param poll: Poll instance to process.
    :type poll: Poll
    :returns: The resulting PollMappingModel value.
    :rtype: PollMappingModel
    """
    return PollMappingModel(
        type="POLL",
        title=poll.title,
        settings=reverse_translate_poll_flags(poll.settings),
        answers=[reverse_translate_poll_answer(answer) for answer in poll.answers],
        poll_id=poll.poll_id,
        version=poll.version,
        state=(
            reverse_translate_poll_state(poll.state) if poll.state is not None else None
        ),
    )


privacy_access_map = {
    PrivacyAccess.ALL: PrivacyAccessMappingModel.ALL,
    PrivacyAccess.CONTACTS: PrivacyAccessMappingModel.CONTACTS,
    PrivacyAccess.NOBODY: PrivacyAccessMappingModel.NOBODY,
}


def reverse_translate_privacy_access(
    privacy_access: PrivacyAccess,
) -> PrivacyAccessMappingModel:
    """Reverse translate privacy access.

    :param privacy_access: PrivacyAccess instance to process.
    :type privacy_access: PrivacyAccess
    :returns: The resulting PrivacyAccessMappingModel value.
    :rtype: PrivacyAccessMappingModel
    """
    return privacy_access_map[privacy_access]


def reverse_translate_privacy_settings(
    privacy_settings: PrivacySettings,
) -> PrivacySettingsMappingModel:
    """Reverse translate privacy settings.

    :param privacy_settings: PrivacySettings instance to process.
    :type privacy_settings: PrivacySettings
    :returns: The resulting PrivacySettingsMappingModel value.
    :rtype: PrivacySettingsMappingModel
    """
    def translate_access(
        value: PrivacyAccess | None,
    ) -> Literal["ALL", "CONTACTS", "_NONE_"] | None:
        if value is None:
            return None
        return cast(  # type: ignore[redundant-cast]
            Literal["ALL", "CONTACTS", "_NONE_"],
            reverse_translate_privacy_access(value).value,
        )

    return PrivacySettingsMappingModel(
        search_by_phone=translate_access(privacy_settings.search_by_phone),
        incoming_calls=translate_access(privacy_settings.incoming_calls),
        chat_invites=translate_access(privacy_settings.chat_invites),
        phone_number_visibility=translate_access(
            privacy_settings.phone_number_visibility
        ),
        hide_online_status=privacy_settings.hide_online_status,
        safe_content_only=privacy_settings.safe_content_only,
    )
