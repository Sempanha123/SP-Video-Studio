import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15
import QtMultimedia
import "../components"
import "../theme"

FocusScope {
    id: root
    property var controller
    focus: true

    function loadSelection() {
        player.stop()
        player.source = ""
        if (!root.controller) return
        if ((root.controller.selectedType === "video" || root.controller.selectedType === "audio") && root.controller.sourceUrl !== "")
            player.source = root.controller.sourceUrl
    }

    Keys.onSpacePressed: function(event) {
        if (root.controller && (root.controller.selectedType === "video" || root.controller.selectedType === "audio")) {
            root.controller.togglePlayback()
            event.accepted = true
        }
    }
    Keys.onLeftPressed: function(event) {
        if (root.controller) {
            root.controller.keyboardSeek(-1, (event.modifiers & Qt.ShiftModifier) !== 0)
            event.accepted = true
        }
    }
    Keys.onRightPressed: function(event) {
        if (root.controller) {
            root.controller.keyboardSeek(1, (event.modifiers & Qt.ShiftModifier) !== 0)
            event.accepted = true
        }
    }
    Keys.onPressed: function(event) {
        if (root.controller && event.key === Qt.Key_M && event.modifiers === Qt.NoModifier) {
            root.controller.toggleMute()
            event.accepted = true
        }
    }

    Rectangle {
        anchors.fill: parent
        radius: Theme.radius.large
        color: Theme.colors.surfaceRaised
        border.color: Theme.colors.border
        border.width: 1
        clip: true

        ColumnLayout {
            anchors.fill: parent
            anchors.margins: Theme.spacing.md
            spacing: Theme.spacing.sm

            Item {
                id: viewport
                Layout.fillWidth: true
                Layout.fillHeight: true
                Layout.minimumHeight: 260

                Rectangle {
                    anchors.fill: parent
                    radius: Theme.radius.medium
                    color: Theme.colors.background
                    border.color: Theme.colors.border
                    border.width: 1
                    clip: true

                    VideoOutput {
                        id: videoOutput
                        anchors.fill: parent
                        visible: root.controller && root.controller.selectedType === "video" && root.controller.state !== "error"
                        fillMode: VideoOutput.PreserveAspectFit
                    }

                    ImagePreview {
                        anchors.fill: parent
                        visible: root.controller && root.controller.selectedType === "image"
                        sourceUrl: root.controller ? root.controller.sourceUrl : ""
                    }

                    AudioPreview {
                        anchors.fill: parent
                        visible: root.controller && root.controller.selectedType === "audio" && root.controller.state !== "error"
                        media: root.controller ? root.controller.selectedMedia : ({})
                    }

                    EmptyState {
                        anchors.centerIn: parent
                        visible: !root.controller || root.controller.selectedMediaId === ""
                        iconName: "video"
                        title: "Select media to preview"
                        description: "Choose a video, image or audio file from your project library."
                    }

                    LoadingState {
                        anchors.centerIn: parent
                        visible: root.controller && root.controller.selectedMediaId !== "" && root.controller.state === "loading"
                        text: "Loading preview…"
                    }

                    PlayerErrorState {
                        anchors.centerIn: parent
                        visible: root.controller && root.controller.state === "error"
                        controller: root.controller
                    }

                    TapHandler {
                        acceptedButtons: Qt.LeftButton
                        onTapped: root.forceActiveFocus()
                    }
                }
            }

            MediaInfoStrip {
                Layout.fillWidth: true
                visible: root.controller && root.controller.selectedMediaId !== ""
                media: root.controller ? root.controller.selectedMedia : ({})
            }

            PlayerControls {
                Layout.fillWidth: true
                controller: root.controller
            }
        }
    }

    AudioOutput {
        id: audioOutput
        volume: root.controller ? root.controller.volume / 100.0 : 1.0
        muted: root.controller ? root.controller.muted : false
    }

    MediaPlayer {
        id: player
        audioOutput: audioOutput
        videoOutput: videoOutput

        onPositionChanged: if (root.controller) root.controller.backendPositionChanged(position)
        onDurationChanged: if (root.controller) root.controller.backendDurationChanged(duration)
        onPlaybackStateChanged: {
            if (!root.controller) return
            if (playbackState === MediaPlayer.PlayingState) root.controller.backendPlaybackStateChanged("playing")
            else if (playbackState === MediaPlayer.PausedState) root.controller.backendPlaybackStateChanged("paused")
            else root.controller.backendPlaybackStateChanged("stopped")
        }
        onMediaStatusChanged: {
            if (!root.controller) return
            if (mediaStatus === MediaPlayer.LoadingMedia || mediaStatus === MediaPlayer.BufferingMedia)
                root.controller.backendMediaStatusChanged("loading")
            else if (mediaStatus === MediaPlayer.LoadedMedia || mediaStatus === MediaPlayer.BufferedMedia)
                root.controller.backendMediaStatusChanged("ready")
            else if (mediaStatus === MediaPlayer.EndOfMedia)
                root.controller.backendEndOfMedia()
            else if (mediaStatus === MediaPlayer.InvalidMedia)
                root.controller.backendError(errorString || "The local multimedia backend could not decode this file.")
        }
        onErrorOccurred: function(error, errorString) {
            if (root.controller && error !== MediaPlayer.NoError)
                root.controller.backendError(errorString || "The local multimedia backend could not preview this file.")
        }
    }

    Connections {
        target: root.controller
        ignoreUnknownSignals: true
        function onSelectedMediaChanged() { root.loadSelection() }
        function onPlayRequested() { player.play() }
        function onPauseRequested() { player.pause() }
        function onStopRequested() { player.stop() }
        function onSeekRequested(position) { player.position = position }
        function onReleaseRequested() { player.stop(); player.source = "" }
    }

    Component.onCompleted: loadSelection()
    Component.onDestruction: {
        player.stop()
        player.source = ""
    }
}
