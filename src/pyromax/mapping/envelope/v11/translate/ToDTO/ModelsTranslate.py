import operator
from abc import ABC, abstractmethod
from functools import reduce
from typing import cast, Generic, Any, TYPE_CHECKING, Literal
from enum import Enum

from typing_extensions import TypeVar

from ...payloads.responses import CreateGroupResponse
from ...payloads.shared import (
    CamelCaseModel,
    PollAnswerMappingModel,
    PollFlagsMappingModel,
)
from ......models import (
    Contact,
    DelayedAttributes,
    Message,
    MessageLink,
    BaseMaxObject,
    BaseFileAttachment,
    EmojiReaction,
    ReadState,
    Chat,
    Name,
    Profile,
    Presence,
    Member,
    Folder,
    FolderUpdate,
    FolderList,
    Session,
    Poll,
    PollState,
    PollResult,
    PollVote,
    PollAnswer,
    PollFlags,
)
from ...payloads.models import (
    ContactMappingModel,
    MessageMappingModel,
    ReadStateMappingModel,
    MessageLinkMappingModel,
    ReactionInfoMappingModel,
    ChatMappingModel,
    NameMappingModel,
    ProfileMappingModel,
    PresenceMappingModel,
    MemberMappingModel,
    FolderMappingModel,
    FolderUpdateMappingModel,
    FolderListMappingModel,
    SessionMappingModel,
    PollMappingModel,
    PollVoteMappingModel,
    PollStateMappingModel,
    PollResultMappingModel,
)

TranslateObj = TypeVar("TranslateObj", bound=CamelCaseModel | Enum)
ReturnObj = TypeVar(
    "ReturnObj", bound=BaseMaxObject | BaseFileAttachment | Enum, default=BaseMaxObject
)


class BaseTranslateMappingModel(ABC, Generic[TranslateObj, ReturnObj]):

    if TYPE_CHECKING:

        @staticmethod
        @abstractmethod
        def translate(*args: Any, **kwargs: Any) -> ReturnObj:
            """Translate the mapping payload into ReturnObj.

            :param args: Positional arguments forwarded to the wrapped callable.
            :type args: Any
            :param kwargs: Keyword arguments forwarded to the wrapped callable.
            :type kwargs: Any
            :returns: The resulting ReturnObj value.
            :rtype: ReturnObj
            """
            pass

    else:

        @staticmethod
        @abstractmethod
        def translate(
            mapping_model: TranslateObj, *args: Any, **kwargs: Any
        ) -> BaseMaxObject:
            """Translate the mapping payload into BaseMaxObject.

            :param mapping_model: Mapping model to translate.
            :type mapping_model: TranslateObj
            :param args: Positional arguments forwarded to the wrapped callable.
            :type args: Any
            :param kwargs: Keyword arguments forwarded to the wrapped callable.
            :type kwargs: Any
            :returns: The resulting BaseMaxObject value.
            :rtype: BaseMaxObject
            """
            pass


class TranslateName(BaseTranslateMappingModel[NameMappingModel]):
    @staticmethod
    def translate(
        mapping_model: NameMappingModel,
    ) -> Name:
        """Translate translate between mapping and public models.

        :param mapping_model: Mapping model to translate.
        :type mapping_model: NameMappingModel
        :returns: The translated Name instance.
        :rtype: Name
        """
        return Name(
            name=mapping_model.name,
            first_name=mapping_model.first_name,
            last_name=mapping_model.last_name,
            type=mapping_model.type,
        )


class TranslateContact(BaseTranslateMappingModel[ContactMappingModel]):
    @staticmethod
    def translate(contact: ContactMappingModel) -> Contact:
        """Translate translate between mapping and public models.

        :param contact: ContactMappingModel instance to process.
        :type contact: ContactMappingModel
        :returns: The translated Contact instance.
        :rtype: Contact
        """
        return Contact(
            id=contact.id,
            names=[TranslateName.translate(name) for name in contact.names],
            description=contact.description,
            first_name=contact.names[0].first_name if contact.names else "",
            last_name=contact.names[0].last_name if contact.names else "",
            phone=str(contact.phone),
            avatar_url=contact.base_url,
            raw_avatar_url=contact.base_raw_url,
            photo_id=str(contact.photo_id),
            country=contact.country,
            account_status=contact.account_status,
            email=contact.email,
            registration_time=contact.registration_time,
            update_time=contact.update_time,
            options=contact.options,
            status=contact.status,
            gender=contact.gender,
            link=contact.link,
            web_app=contact.web_app,
            menu_button=contact.menu_button,
        )


class TranslateProfile(BaseTranslateMappingModel[ProfileMappingModel]):
    @staticmethod
    def translate(profile: ProfileMappingModel) -> Profile:
        """Translate translate between mapping and public models.

        :param profile: ProfileMappingModel instance to process.
        :type profile: ProfileMappingModel
        :returns: The translated Profile instance.
        :rtype: Profile
        """
        profile_options = []
        for option in profile.profile_options:
            if isinstance(option, int):
                profile_options.append(option)
            elif isinstance(option, str) and option.isdigit():
                profile_options.append(int(option))
        return Profile(
            contact=TranslateContact.translate(profile.contact),
            profile_options=profile_options,
        )


class TranslatePresence(BaseTranslateMappingModel[PresenceMappingModel]):
    @staticmethod
    def translate(presence: PresenceMappingModel) -> Presence:
        """Translate translate between mapping and public models.

        :param presence: PresenceMappingModel instance to process.
        :type presence: PresenceMappingModel
        :returns: The translated Presence instance.
        :rtype: Presence
        """
        return Presence(
            seen=presence.seen,
            status=presence.status,
        )


class TranslateMember(BaseTranslateMappingModel[MemberMappingModel]):
    @staticmethod
    def translate(member: MemberMappingModel) -> Member:
        """Translate translate between mapping and public models.

        :param member: MemberMappingModel instance to process.
        :type member: MemberMappingModel
        :returns: The translated Member instance.
        :rtype: Member
        """
        return Member(
            presence=TranslatePresence.translate(member.presence),
            contact=TranslateContact.translate(member.contact),
        )


class TranslateMessage(BaseTranslateMappingModel[MessageMappingModel]):
    @staticmethod
    def translate(message: MessageMappingModel, fallback_chat_id: int = -1) -> Message:

        """Translate translate between mapping and public models.

        :param message: MessageMappingModel instance to process.
        :type message: MessageMappingModel
        :param fallback_chat_id: Identifier of the fallback chat.
        :type fallback_chat_id: int
        :returns: The translated Message instance.
        :rtype: Message
        """
        def translate_message(msg: MessageMappingModel) -> Message:
            """Translate message between mapping and public models.

            :param msg: MessageMappingModel instance to process.
            :type msg: MessageMappingModel
            :returns: The translated Message instance.
            :rtype: Message
            """
            msg_id = msg.id
            # if message.id is None:
            #     msg_id = 0
            # else:
            #     msg_id = int(msg_id) if type(msg_id) is str and msg_id.isdigit() or type(msg_id) is int else 0

            msg_link = msg.link

            if type(msg_id) is str:
                msg_id = int(msg_id) if msg_id.isdigit() else 0
            elif msg_id is None:
                msg_id = -1
            else:
                msg_id = msg_id

            if msg.chat_id is None:
                chat_id = fallback_chat_id
            else:
                chat_id = msg.chat_id

            if msg.time is None:
                msg_time = -1
            else:
                msg_time = msg.time

            delayed_attributes = (
                DelayedAttributes(
                    time_to_fire=msg.delayed_attributes.time_to_fire,
                    notify_sender=msg.delayed_attributes.notify_sender,
                    notify_opponents=msg.delayed_attributes.notify_opponents,
                )
                if msg.delayed_attributes is not None
                else None
            )
            if msg_link is not None and msg_link.message is not None:
                return Message(
                    message_id=cast(int, msg_id),
                    type=msg.type,
                    chat_id=chat_id,
                    cid=msg.cid,
                    time=msg_time,
                    text=msg.text,
                    status=msg.status,
                    elements=msg.elements,
                    sender_id=msg.sender,
                    attaches=msg.attaches,
                    delayed_attributes=delayed_attributes,
                    link=MessageLink(
                        message=translate_message(msg=msg_link.message),
                        message_id=msg_link.message_id,
                        type=msg_link.type,
                    ),
                )

            return Message(
                message_id=cast(int, msg_id),
                type=msg.type,
                chat_id=chat_id,
                cid=msg.cid,
                time=msg_time,
                text=msg.text,
                status=msg.status,
                elements=msg.elements,
                sender_id=msg.sender,
                attaches=msg.attaches,
                delayed_attributes=delayed_attributes,
            )

        return translate_message(msg=message)


class TranslateReactionInfo(BaseTranslateMappingModel[ReactionInfoMappingModel]):

    @staticmethod
    def translate(
        reaction: ReactionInfoMappingModel,
        chat_id: int,
        message_id: int | str,
        status: str = "ADD",
    ) -> EmojiReaction:
        """Translate translate between mapping and public models.

        :param reaction: ReactionInfoMappingModel instance to process.
        :type reaction: ReactionInfoMappingModel
        :param chat_id: Identifier of the chat.
        :type chat_id: int
        :param message_id: Identifier of the message.
        :type message_id: int | str
        :param status: The status value.
        :type status: str
        :returns: The translated EmojiReaction instance.
        :rtype: EmojiReaction
        """
        from ......models.EmojiReaction import Counters

        return EmojiReaction(
            chat_id=chat_id,
            message_id=message_id,
            counters=cast(list[Counters] | None, reaction.counters),
            total_count=reaction.total_count,
            your_reaction=reaction.your_reaction,
            status=cast(Literal["ADD", "REMOVE"], status),
        )


class TranslateReadState(BaseTranslateMappingModel[ReadStateMappingModel]):
    @staticmethod
    def translate(
        read_state: ReadStateMappingModel,
        chat_id: int,
        message_id: int | str,
    ) -> ReadState:
        """Translate translate between mapping and public models.

        :param read_state: ReadStateMappingModel instance to process.
        :type read_state: ReadStateMappingModel
        :param chat_id: Identifier of the chat.
        :type chat_id: int
        :param message_id: Identifier of the message.
        :type message_id: int | str
        :returns: The translated ReadState instance.
        :rtype: ReadState
        """
        return ReadState(
            chat_id=chat_id,
            message_id=message_id,
            mark=read_state.mark,
            unread=read_state.unread,
        )


class TranslateChat(BaseTranslateMappingModel[ChatMappingModel]):
    @staticmethod
    def translate(chat: ChatMappingModel) -> Chat:
        """Translate translate between mapping and public models.

        :param chat: ChatMappingModel instance to process.
        :type chat: ChatMappingModel
        :returns: The translated Chat instance.
        :rtype: Chat
        """
        return Chat(
            id=chat.id,
            type=chat.type,
            status=chat.status,
            owner=chat.owner,
            participants=chat.participants,
            title=chat.title,
            base_raw_icon_url=chat.base_raw_icon_url,
            base_icon_url=chat.base_icon_url,
            last_message=(
                TranslateMessage.translate(
                    message=chat.last_message, fallback_chat_id=chat.id
                )
                if chat.last_message
                else None
            ),
            last_event_time=chat.last_event_time,
            last_delayed_update_time=chat.last_delayed_update_time,
            last_fire_delayed_error_time=chat.last_fire_delayed_error_time,
            created=chat.created,
            new_messages=chat.new_messages,
            link=chat.link,
            access=chat.access,
            restrictions=chat.restrictions,
            pinned_message=(
                TranslateMessage.translate(
                    message=chat.pinned_message, fallback_chat_id=chat.id
                )
                if chat.pinned_message
                else None
            ),
            participants_count=chat.participants_count,
            description=chat.description,
            options=chat.options,
            join_time=chat.join_time,
            invited_by=chat.invited_by,
            modified=chat.modified,
            messages_count=chat.messages_count,
            has_bots=chat.has_bots,
            prev_message_id=chat.prev_message_id,
            admin_participants=chat.admin_participants,
            admins=chat.admins,
            cid=chat.cid,
        )


class TranslateFolder(BaseTranslateMappingModel[FolderMappingModel]):
    @staticmethod
    def translate(folder: FolderMappingModel) -> Folder:
        """Translate translate between mapping and public models.

        :param folder: FolderMappingModel instance to process.
        :type folder: FolderMappingModel
        :returns: The translated Folder instance.
        :rtype: Folder
        """
        return Folder(
            source_id=folder.source_id,
            include=folder.include,
            options=folder.options,
            update_time=folder.update_time,
            id=folder.id,
            filters=folder.filters,
            title=folder.title,
        )


class TranslateFolderUpdate(BaseTranslateMappingModel[FolderUpdateMappingModel]):

    @staticmethod
    def translate(folder_update: FolderUpdateMappingModel) -> FolderUpdate:
        """Translate translate between mapping and public models.

        :param folder_update: FolderUpdateMappingModel instance to process.
        :type folder_update: FolderUpdateMappingModel
        :returns: The translated FolderUpdate instance.
        :rtype: FolderUpdate
        """
        return FolderUpdate(
            folder_sync=folder_update.folder_sync,
            folders_order=folder_update.folders_order,
            folder=(
                TranslateFolder.translate(folder=folder_update.folder)
                if folder_update.folder is not None
                else folder_update.folder
            ),
        )


class TranslateFolderList(BaseTranslateMappingModel[FolderListMappingModel]):

    @staticmethod
    def translate(folder_list: FolderListMappingModel) -> FolderList:
        """Translate translate between mapping and public models.

        :param folder_list: FolderListMappingModel instance to process.
        :type folder_list: FolderListMappingModel
        :returns: The translated FolderList instance.
        :rtype: FolderList
        """
        return FolderList(
            folder_sync=folder_list.folder_sync,
            folders_order=folder_list.folders_order,
            all_filter_exclude_folders=folder_list.all_filter_exclude_folders,
            folders=[
                TranslateFolder.translate(folder) for folder in folder_list.folders
            ],
        )


class TranslateSession(BaseTranslateMappingModel[SessionMappingModel]):
    @staticmethod
    def translate(session: SessionMappingModel) -> Session:
        """Translate translate between mapping and public models.

        :param session: SessionMappingModel instance to process.
        :type session: SessionMappingModel
        :returns: The translated Session instance.
        :rtype: Session
        """
        location = None
        ip = None
        if session.location is not None and ", IP" in session.location:
            location, ip = tuple(
                map(
                    str.strip,
                    session.location.split(", IP"),
                )
            )

        return Session(
            id=session.id,
            device_id=session.device_id,
            current=session.current,
            user_agent=session.user_agent,
            app_version=session.app_version,
            device_name=session.client or session.device_name,
            device_type=session.device_type,
            platform=session.platform,
            ip=ip,
            location=location,
            created=session.created,
            updated=session.updated,
            last_activity=session.last_activity,
            options=session.options,
            info=session.info,
            time=session.time,
        )


class TranslatePollFlags(BaseTranslateMappingModel[PollFlagsMappingModel, PollFlags]):
    @staticmethod
    def translate(poll_flags: PollFlagsMappingModel) -> PollFlags:
        """Translate translate between mapping and public models.

        :param poll_flags: PollFlagsMappingModel instance to process.
        :type poll_flags: PollFlagsMappingModel
        :returns: The translated PollFlags instance.
        :rtype: PollFlags
        """
        poll_flags_map: dict[PollFlagsMappingModel, PollFlags] = {
            PollFlagsMappingModel.FLAG_SETTINGS_QUIZ: PollFlags.FLAG_SETTINGS_QUIZ,
            PollFlagsMappingModel.FLAG_SETTINGS_CLOSED: PollFlags.FLAG_SETTINGS_CLOSED,
            PollFlagsMappingModel.FLAG_SETTINGS_REVOTE: PollFlags.FLAG_SETTINGS_REVOTE,
            PollFlagsMappingModel.FLAG_SETTINGS_MULTISELECT: PollFlags.FLAG_SETTINGS_MULTISELECT,
            PollFlagsMappingModel.FLAG_SETTINGS_CAN_FORWARD: PollFlags.FLAG_SETTINGS_CAN_FORWARD,
            PollFlagsMappingModel.FLAG_SETTINGS_ANONYMOUS: PollFlags.FLAG_SETTINGS_ANONYMOUS,
        }

        flags = [poll_flags_map[poll_flag] for poll_flag in poll_flags]

        if not flags:
            return PollFlags(0)

        return reduce(operator.or_, flags)


class TranslatePollAnswer(BaseTranslateMappingModel[PollAnswerMappingModel]):
    @staticmethod
    def translate(poll_answer: PollAnswerMappingModel) -> PollAnswer:
        """Translate translate between mapping and public models.

        :param poll_answer: PollAnswerMappingModel instance to process.
        :type poll_answer: PollAnswerMappingModel
        :returns: The translated PollAnswer instance.
        :rtype: PollAnswer
        """
        return PollAnswer(
            answer_id=poll_answer.answer_id,
            text=poll_answer.text,
        )


class TranslatePollVote(BaseTranslateMappingModel[PollVoteMappingModel]):
    @staticmethod
    def translate(poll_vote: PollVoteMappingModel) -> PollVote:
        """Translate translate between mapping and public models.

        :param poll_vote: PollVoteMappingModel instance to process.
        :type poll_vote: PollVoteMappingModel
        :returns: The translated PollVote instance.
        :rtype: PollVote
        """
        return PollVote(
            timestamp=poll_vote.timestamp,
            user_id=poll_vote.user_id,
        )


class TranslatePollResult(BaseTranslateMappingModel[PollResultMappingModel]):
    @staticmethod
    def translate(poll_result: PollResultMappingModel) -> PollResult:
        """Translate translate between mapping and public models.

        :param poll_result: PollResultMappingModel instance to process.
        :type poll_result: PollResultMappingModel
        :returns: The translated PollResult instance.
        :rtype: PollResult
        """
        return PollResult(
            votes=[TranslatePollVote.translate(vote) for vote in poll_result.votes],
            vote_count=poll_result.vote_count,
            rate=poll_result.rate,
            answer_id=poll_result.answer_id,
            options=poll_result.options,
        )


class TranslatePollState(BaseTranslateMappingModel[PollStateMappingModel]):
    @staticmethod
    def translate(poll_state: PollStateMappingModel) -> PollState:
        """Translate translate between mapping and public models.

        :param poll_state: PollStateMappingModel instance to process.
        :type poll_state: PollStateMappingModel
        :returns: The translated PollState instance.
        :rtype: PollState
        """
        poll_result = (
            [TranslatePollResult.translate(res) for res in poll_state.result]
            if poll_state.result is not None
            else None
        )
        return PollState(
            total=poll_state.total,
            voter_preview_ids=poll_state.voter_preview_ids,
            result=poll_result,
        )


class TranslatePoll(BaseTranslateMappingModel[PollMappingModel, Poll]):
    @staticmethod
    def translate(poll: PollMappingModel) -> Poll:
        """Translate translate between mapping and public models.

        :param poll: PollMappingModel instance to process.
        :type poll: PollMappingModel
        :returns: The translated Poll instance.
        :rtype: Poll
        """
        return Poll(
            title=poll.title,
            settings=TranslatePollFlags.translate(poll.settings),
            answers=[TranslatePollAnswer.translate(answer) for answer in poll.answers],
            poll_id=poll.poll_id,
            version=poll.version,
            state=(
                TranslatePollState.translate(poll.state)
                if poll.state is not None
                else None
            ),
        )


TRANSLATE_MAPPING_MODELS: dict[
    type[CamelCaseModel] | type[Enum], type[BaseTranslateMappingModel[Any, Any]]
] = {
    ContactMappingModel: TranslateContact,
    MessageMappingModel: TranslateMessage,
    ReactionInfoMappingModel: TranslateReactionInfo,
    ReadStateMappingModel: TranslateReadState,
    ChatMappingModel: TranslateChat,
    NameMappingModel: TranslateName,
    ProfileMappingModel: TranslateProfile,
    PresenceMappingModel: TranslatePresence,
    MemberMappingModel: TranslateMember,
    FolderMappingModel: TranslateFolder,
    FolderUpdateMappingModel: TranslateFolderUpdate,
    FolderListMappingModel: TranslateFolderList,
    SessionMappingModel: TranslateSession,
    PollAnswerMappingModel: TranslatePollAnswer,
    PollFlagsMappingModel: TranslatePollFlags,
    PollResultMappingModel: TranslatePollResult,
    PollStateMappingModel: TranslatePollState,
    PollVoteMappingModel: TranslatePollVote,
    PollMappingModel: TranslatePoll,
}


def translate_models(
    mapping_obj: CamelCaseModel, *args: Any, **kwargs: Any
) -> BaseMaxObject | BaseFileAttachment | CamelCaseModel:
    """Translate models.

    :param mapping_obj: CamelCaseModel instance to process.
    :type mapping_obj: CamelCaseModel
    :param args: Positional arguments forwarded to the wrapped callable.
    :type args: Any
    :param kwargs: Keyword arguments forwarded to the wrapped callable.
    :type kwargs: Any
    :returns: The resulting BaseMaxObject | BaseFileAttachment | CamelCaseModel value.
    :rtype: BaseMaxObject | BaseFileAttachment | CamelCaseModel
    """
    translate_model = TRANSLATE_MAPPING_MODELS.get(type(mapping_obj), None)
    if translate_model is None:
        return mapping_obj

    translated_obj = cast(
        BaseMaxObject | BaseFileAttachment | CamelCaseModel,
        translate_model.translate(mapping_obj, *args, **kwargs),
    )

    return translated_obj
