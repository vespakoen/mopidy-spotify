from __future__ import unicode_literals

import logging

from mopidy import backend

import spotify

from mopidy_spotify import translator, utils


logger = logging.getLogger(__name__)


class SpotifyPlaylistsProvider(backend.PlaylistsProvider):

    def __init__(self, backend):
        self._backend = backend

        # TODO Listen to playlist events

    def create(self, name):
        try:
            sp_playlist = (
                self._backend._session.playlist_container
                .add_new_playlist(name))
        except ValueError as exc:
            logger.warning(
                'Failed creating new Spotify playlist "%s": %s', name, exc)
        except spotify.Error:
            logger.warning('Failed creating new Spotify playlist "%s"', name)
        else:
            username = self._backend._session.user_name
            return translator.to_playlist(sp_playlist, username=username)

    def delete(self, uri):
        pass  # TODO

    def lookup(self, uri):
        try:
            sp_playlist = self._backend._session.get_playlist(uri)
        except spotify.Error as exc:
            logger.debug('Failed to lookup Spotify URI %s: %s', uri, exc)
            return

        if not sp_playlist.is_loaded:
            logger.debug(
                'Waiting for Spotify playlist to load: %s', sp_playlist)
            sp_playlist.load()

        username = self._backend._session.user_name
        return translator.to_playlist(
            sp_playlist, username=username, bitrate=self._backend._bitrate)

    @property
    def playlists(self):
        # XXX We should just return light-weight Ref objects here, but Mopidy's
        # core and backend APIs must be changed first.

        with utils.time_logger('Playlist fetch'):
            return (
                list(self._get_starred_playlist()) +
                list(self._get_flattened_playlists()))

    def _get_starred_playlist(self):
        if self._backend._session is None:
            return

        sp_starred = self._backend._session.get_starred()
        if sp_starred is None:
            return

        sp_starred.load()

        starred = translator.to_playlist(
            sp_starred,
            username=self._backend._session.user_name,
            bitrate=self._backend._bitrate)

        if starred is not None:
            yield starred

    def _get_flattened_playlists(self):
        if self._backend._session is None:
            return

        if self._backend._session.playlist_container is None:
            return

        username = self._backend._session.user_name
        folders = []

        for sp_playlist in self._backend._session.playlist_container:
            if isinstance(sp_playlist, spotify.PlaylistFolder):
                if sp_playlist.type is spotify.PlaylistType.START_FOLDER:
                    folders.append(sp_playlist.name)
                elif sp_playlist.type is spotify.PlaylistType.END_FOLDER:
                    folders.pop()
                continue

            playlist = translator.to_playlist(
                sp_playlist, folders=folders, username=username,
                bitrate=self._backend._bitrate)
            if playlist is not None:
                yield playlist

    def refresh(self):
        pass  # Not needed as long as we don't cache anything.

    def save(self, playlist):
        pass  # TODO
