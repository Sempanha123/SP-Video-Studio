import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15
import QtQuick.Dialogs
import "../theme"
import "../components"
import "../editor"

Item {
    id: root
    property string actionProjectId: typeof projectController !== "undefined" ? (projectController.currentProject.id || "") : ""
    property string selectedMediaId: ""
    property string removeMediaId: ""
    property string removeMediaName: ""
    property bool gridView: true
    property bool dropActive: false
    property string workspaceMode: "media"
    signal navigateRequested(string page, string workflow)
    signal toastRequested(string message, string variant)

    function current() {
        return typeof projectController !== "undefined" ? projectController.currentProject : ({})
    }

    function selectMedia(mediaId) {
        root.selectedMediaId = mediaId
        if (typeof playbackController !== "undefined")
            playbackController.setMedia(mediaId)
        if (typeof transcriptionController !== "undefined")
            transcriptionController.setMedia(mediaId)
    }

    function setWorkspaceMode(mode) {
        if (mode === root.workspaceMode) return
        if (root.workspaceMode === "script" && typeof scriptController !== "undefined" && !scriptController.flush()) return
        if (root.workspaceMode === "transcription" && typeof transcriptionController !== "undefined" && !transcriptionController.saveEdits()) return
        if (mode === "script") {
            if (typeof playbackController !== "undefined") playbackController.clear()
            if (typeof scriptController !== "undefined" && !scriptController.load(root.current().id || "")) return
        }
        if (mode === "transcription" && typeof transcriptionController !== "undefined")
            transcriptionController.setMedia(root.selectedMediaId)
        root.workspaceMode = mode
    }

    function leaveWorkspace() {
        if (typeof scriptController !== "undefined" && !scriptController.flush()) return
        if (typeof transcriptionController !== "undefined" && !transcriptionController.saveEdits()) return
        if (typeof transcriptionController !== "undefined") transcriptionController.cancel()
        if (typeof playbackController !== "undefined") playbackController.clear()
        root.navigateRequested("projects", "")
    }

    function showDetails(mediaId) {
        if (typeof mediaController === "undefined" || mediaId === "") return
        var details = mediaController.mediaDetails(mediaId)
        if (details.id) {
            detailsDialog.details = details
            detailsDialog.open()
        }
    }

    function requestRemove(mediaId, mediaName) {
        root.removeMediaId = mediaId
        root.removeMediaName = mediaName
        removeMediaDialog.open()
    }

    Component.onCompleted: {
        if (typeof mediaController !== "undefined")
            mediaController.setCurrentProject(root.current().id || "")
        if (typeof playbackController !== "undefined")
            playbackController.setCurrentProject(root.current().id || "")
        if (typeof ttsController !== "undefined")
            ttsController.setCurrentProject(root.current().id || "")
        if (typeof transcriptionController !== "undefined")
            transcriptionController.setCurrentProject(root.current().id || "")
    }
    Component.onDestruction: {
        if (typeof scriptController !== "undefined") scriptController.flush()
        if (typeof transcriptionController !== "undefined") { transcriptionController.saveEdits(); transcriptionController.cancel() }
        if (typeof playbackController !== "undefined") playbackController.clear()
    }

    Connections {
        target: typeof projectController !== "undefined" ? projectController : null
        ignoreUnknownSignals: true
        function onCurrentProjectChanged() {
            root.actionProjectId = root.current().id || ""
            root.selectedMediaId = ""
            if (typeof mediaController !== "undefined")
                mediaController.setCurrentProject(root.current().id || "")
            if (typeof playbackController !== "undefined")
                playbackController.setCurrentProject(root.current().id || "")
            if (typeof ttsController !== "undefined")
                ttsController.setCurrentProject(root.current().id || "")
            if (typeof transcriptionController !== "undefined")
                transcriptionController.setCurrentProject(root.current().id || "")
            if (root.workspaceMode === "script" && typeof scriptController !== "undefined")
                scriptController.load(root.current().id || "")
        }
    }

    ColumnLayout {
        anchors.fill: parent
        spacing: Theme.spacing.lg

        RowLayout {
            Layout.fillWidth: true
            spacing: Theme.spacing.md
            SecondaryButton { text: "Projects"; iconName: "back"; onClicked: root.leaveWorkspace() }
            ColumnLayout {
                Layout.fillWidth: true
                spacing: 1
                Text { Layout.fillWidth: true; text: root.current().title || "Project Workspace"; color: Theme.colors.textPrimary; font.family: Theme.type.family; font.pixelSize: Theme.type.titleLarge; font.weight: Theme.type.semibold; elide: Text.ElideRight }
                Text {
                    text: (root.current().workflowName || "Video") + " · " + (root.current().languageName || "English") + " · " + (root.current().aspectRatio || "16:9") + " · " + (root.current().fps || 30) + " FPS"
                    color: Theme.colors.textSecondary
                    font.family: Theme.type.family
                    font.pixelSize: Theme.type.bodySmall
                }
            }
            SecondaryButton { text: "Rename"; iconName: "edit"; onClicked: { renameField.text = root.current().title || ""; renameDialog.open(); renameField.forceActiveFocus() } }
            SecondaryButton {
                text: "Duplicate"; iconName: "copy"
                onClicked: if (typeof projectController !== "undefined") projectController.duplicateProject(root.current().id)
            }
            IconButton { iconName: "trash"; tooltip: "Delete project"; onClicked: deleteDialog.open() }
        }

        RowLayout {
            Layout.fillWidth: true
            spacing: Theme.spacing.sm
            StatusBadge { text: root.current().statusName || "Draft"; status: root.current().status || "offline" }
            Text { text: "Last updated " + (root.current().updatedDisplay || "—"); color: Theme.colors.textMuted; font.family: Theme.type.family; font.pixelSize: Theme.type.caption }
            Item { Layout.fillWidth: true }
            AppButton { text: "Media"; compact: true; variant: root.workspaceMode === "media" ? "secondary" : "ghost"; onClicked: root.setWorkspaceMode("media") }
            AppButton { text: "Script"; compact: true; variant: root.workspaceMode === "script" ? "secondary" : "ghost"; onClicked: root.setWorkspaceMode("script") }
            AppButton { text: "Transcription"; compact: true; variant: root.workspaceMode === "transcription" ? "secondary" : "ghost"; onClicked: root.setWorkspaceMode("transcription") }
        }

        SplitView {
            visible: root.workspaceMode === "media"
            id: workspaceSplit
            Layout.fillWidth: true
            Layout.fillHeight: true
            orientation: root.width < 1080 ? Qt.Vertical : Qt.Horizontal

            AppCard {
                id: libraryCard
                SplitView.preferredWidth: root.width * 0.47
                SplitView.minimumWidth: 460
                SplitView.fillHeight: true
                clip: true

            ColumnLayout {
                anchors.fill: parent
                anchors.margins: Theme.spacing.lg
                spacing: Theme.spacing.md

                RowLayout {
                    Layout.fillWidth: true
                    spacing: Theme.spacing.md
                    ColumnLayout {
                        Layout.fillWidth: true
                        spacing: 1
                        Text { text: "Project Media"; color: Theme.colors.textPrimary; font.family: Theme.type.family; font.pixelSize: Theme.type.heading; font.weight: Theme.type.semibold }
                        Text {
                            text: (typeof mediaController !== "undefined" ? mediaController.visibleCount : 0) + " item" + ((typeof mediaController !== "undefined" && mediaController.visibleCount === 1) ? "" : "s") + " shown"
                            color: Theme.colors.textMuted
                            font.family: Theme.type.family
                            font.pixelSize: Theme.type.caption
                        }
                    }
                    SecondaryButton {
                        visible: root.selectedMediaId !== ""
                        text: "Details"
                        compact: true
                        onClicked: root.showDetails(root.selectedMediaId)
                    }
                    SecondaryButton {
                        visible: root.selectedMediaId !== "" && typeof transcriptionController !== "undefined" && transcriptionController.canTranscribe
                        text: "Transcribe"
                        compact: true
                        onClicked: root.setWorkspaceMode("transcription")
                    }
                    AppButton {
                        text: "Import Media"
                        iconName: "import"
                        onClicked: importDialog.open()
                    }
                }

                RowLayout {
                    Layout.fillWidth: true
                    spacing: Theme.spacing.sm
                    AppTextField {
                        id: searchField
                        Layout.preferredWidth: 230
                        placeholderText: "Search media"
                        onTextChanged: if (typeof mediaController !== "undefined") mediaController.setSearchText(text)
                    }
                    Repeater {
                        model: [
                            { label: "All", value: "all" },
                            { label: "Video", value: "video" },
                            { label: "Audio", value: "audio" },
                            { label: "Images", value: "image" }
                        ]
                        delegate: AppButton {
                            required property var modelData
                            text: modelData.label
                            compact: true
                            variant: (typeof mediaController !== "undefined" && mediaController.typeFilter === modelData.value) ? "secondary" : "ghost"
                            onClicked: if (typeof mediaController !== "undefined") mediaController.setTypeFilter(modelData.value)
                        }
                    }
                    Item { Layout.fillWidth: true }
                    AppComboBox {
                        id: sortCombo
                        Layout.preferredWidth: 154
                        model: ["Recently Added", "Name", "Type", "File Size"]
                        onActivated: {
                            var values = ["recent", "name", "type", "size"]
                            if (typeof mediaController !== "undefined") mediaController.setSortMode(values[currentIndex])
                        }
                    }
                    Rectangle { Layout.preferredWidth: 1; Layout.preferredHeight: 24; color: Theme.colors.border }
                    IconButton { iconName: "grid"; tooltip: "Grid view"; enabled: !root.gridView; onClicked: root.gridView = true }
                    IconButton { iconName: "list"; tooltip: "List view"; enabled: root.gridView; onClicked: root.gridView = false }
                }

                AppCard {
                    Layout.fillWidth: true
                    Layout.preferredHeight: 82
                    visible: typeof mediaController !== "undefined" && mediaController.importing
                    RowLayout {
                        anchors.fill: parent
                        anchors.margins: Theme.spacing.md
                        spacing: Theme.spacing.md
                        ColumnLayout {
                            Layout.fillWidth: true
                            spacing: Theme.spacing.sm
                            Text { Layout.fillWidth: true; text: mediaController.importStatus; color: Theme.colors.textPrimary; font.family: Theme.type.family; font.pixelSize: Theme.type.bodySmall; font.weight: Theme.type.semibold; elide: Text.ElideMiddle }
                            ProgressBar {
                                id: importProgress
                                Layout.fillWidth: true
                                from: 0
                                to: 1
                                value: mediaController.importProgress
                                background: Rectangle { implicitHeight: 6; radius: 3; color: Theme.colors.surfacePressed }
                                contentItem: Item {
                                    implicitHeight: 6
                                    Rectangle { width: importProgress.visualPosition * parent.width; height: parent.height; radius: 3; color: Theme.colors.accent }
                                }
                            }
                        }
                        SecondaryButton { text: "Cancel"; compact: true; onClicked: mediaController.cancelImport() }
                    }
                }

                Item {
                    id: mediaArea
                    Layout.fillWidth: true
                    Layout.fillHeight: true
                    Layout.minimumHeight: 260

                    DropArea {
                        id: dropArea
                        anchors.fill: parent
                        onEntered: function(drag) { root.dropActive = drag.hasUrls }
                        onExited: root.dropActive = false
                        onDropped: function(drop) {
                            root.dropActive = false
                            if (drop.hasUrls && typeof mediaController !== "undefined") {
                                if (mediaController.importUrls(drop.urls)) drop.acceptProposedAction()
                            }
                        }
                    }

                    EmptyState {
                        anchors.centerIn: parent
                        visible: typeof mediaController === "undefined" || (mediaController.visibleCount === 0 && !mediaController.importing)
                        iconName: "assets"
                        title: searchField.text.length > 0 ? "No matching media" : "No media yet"
                        description: searchField.text.length > 0 ? "Try another search or media type." : "Import videos, images or audio to start building your project. You can also drop local files here."
                        actionText: searchField.text.length > 0 ? "" : "Import Media"
                        onActionClicked: importDialog.open()
                    }

                    GridView {
                        id: mediaGrid
                        anchors.fill: parent
                        visible: root.gridView && typeof mediaController !== "undefined" && mediaController.visibleCount > 0
                        clip: true
                        model: typeof mediaController !== "undefined" ? mediaController.model : null
                        cellWidth: 232
                        cellHeight: 242
                        boundsBehavior: Flickable.StopAtBounds
                        ScrollBar.vertical: ScrollBar {}
                        delegate: MediaCard {
                            width: mediaGrid.cellWidth - Theme.spacing.md
                            height: 226
                            mediaId: model.mediaId
                            mediaName: model.name
                            mediaType: model.mediaType
                            typeName: model.typeName
                            thumbnail: model.thumbnail
                            duration: model.duration
                            resolution: model.resolution
                            fileSize: model.fileSize
                            mediaStatus: model.status
                            statusName: model.statusName
                            isSelected: root.selectedMediaId === model.mediaId
                            onActivated: function(id) { root.selectMedia(id) }
                            onDetailsRequested: function(id) { root.showDetails(id) }
                            onRevealRequested: function(id) { mediaController.revealMedia(id) }
                            onRemoveRequested: function(id, label) { root.requestRemove(id, label) }
                        }
                    }

                    ListView {
                        id: mediaList
                        anchors.fill: parent
                        visible: !root.gridView && typeof mediaController !== "undefined" && mediaController.visibleCount > 0
                        clip: true
                        spacing: Theme.spacing.xs
                        model: typeof mediaController !== "undefined" ? mediaController.model : null
                        boundsBehavior: Flickable.StopAtBounds
                        ScrollBar.vertical: ScrollBar {}
                        header: Rectangle {
                            width: mediaList.width
                            height: 34
                            color: Theme.colors.surface
                            RowLayout {
                                anchors.fill: parent
                                anchors.leftMargin: 96
                                anchors.rightMargin: Theme.spacing.sm
                                spacing: Theme.spacing.md
                                Text { Layout.fillWidth: true; text: "Name"; color: Theme.colors.textMuted; font.family: Theme.type.family; font.pixelSize: Theme.type.caption }
                                Text { Layout.preferredWidth: 86; text: "Duration"; color: Theme.colors.textMuted; font.family: Theme.type.family; font.pixelSize: Theme.type.caption }
                                Text { Layout.preferredWidth: 122; text: "Resolution"; color: Theme.colors.textMuted; font.family: Theme.type.family; font.pixelSize: Theme.type.caption }
                                Text { Layout.preferredWidth: 88; text: "Size"; color: Theme.colors.textMuted; font.family: Theme.type.family; font.pixelSize: Theme.type.caption }
                                Item { Layout.preferredWidth: 118 }
                                Item { Layout.preferredWidth: 36 }
                            }
                        }
                        delegate: MediaListRow {
                            width: mediaList.width
                            mediaId: model.mediaId
                            mediaName: model.name
                            mediaType: model.mediaType
                            typeName: model.typeName
                            thumbnail: model.thumbnail
                            duration: model.duration
                            resolution: model.resolution
                            fileSize: model.fileSize
                            mediaStatus: model.status
                            statusName: model.statusName
                            isSelected: root.selectedMediaId === model.mediaId
                            onActivated: function(id) { root.selectMedia(id) }
                            onDetailsRequested: function(id) { root.showDetails(id) }
                            onRevealRequested: function(id) { mediaController.revealMedia(id) }
                            onRemoveRequested: function(id, label) { root.requestRemove(id, label) }
                        }
                    }

                    Rectangle {
                        anchors.fill: parent
                        visible: root.dropActive
                        z: 40
                        radius: Theme.radius.large
                        color: Theme.colors.accentSoft
                        border.color: Theme.colors.accent
                        border.width: 2
                        opacity: 0.96
                        Column {
                            anchors.centerIn: parent
                            spacing: Theme.spacing.md
                            Icon { anchors.horizontalCenter: parent.horizontalCenter; width: 38; height: 38; name: "import" }
                            Text { anchors.horizontalCenter: parent.horizontalCenter; text: "Drop files to import"; color: Theme.colors.accent; font.family: Theme.type.family; font.pixelSize: Theme.type.heading; font.weight: Theme.type.semibold }
                            Text { anchors.horizontalCenter: parent.horizontalCenter; text: "Videos, audio and images"; color: Theme.colors.textSecondary; font.family: Theme.type.family; font.pixelSize: Theme.type.bodySmall }
                        }
                    }
                }
            }
        }

            PreviewPlayer {
                id: previewPlayer
                SplitView.fillWidth: true
                SplitView.fillHeight: true
                SplitView.minimumWidth: workspaceSplit.orientation === Qt.Horizontal ? 420 : 0
                SplitView.minimumHeight: workspaceSplit.orientation === Qt.Vertical ? 300 : 0
                controller: typeof playbackController !== "undefined" ? playbackController : null
            }
        }

        SplitView {
            visible: root.workspaceMode === "transcription"
            Layout.fillWidth: true
            Layout.fillHeight: true
            orientation: root.width < 1120 ? Qt.Vertical : Qt.Horizontal

            TranscriptionPanel {
                SplitView.fillWidth: true
                SplitView.fillHeight: true
                SplitView.preferredWidth: root.width * 0.60
                SplitView.minimumWidth: 520
                controller: typeof transcriptionController !== "undefined" ? transcriptionController : null
                playbackController: typeof playbackController !== "undefined" ? playbackController : null
                onNavigateRequested: function(page, workflow) { root.navigateRequested(page, workflow) }
                onToastRequested: function(message, variant) { root.toastRequested(message, variant) }
            }

            PreviewPlayer {
                SplitView.fillWidth: true
                SplitView.fillHeight: true
                SplitView.preferredWidth: root.width * 0.40
                SplitView.minimumWidth: 360
                controller: typeof playbackController !== "undefined" ? playbackController : null
            }
        }

        ScriptEditor {
            Layout.fillWidth: true
            Layout.fillHeight: true
            visible: root.workspaceMode === "script"
            controller: typeof scriptController !== "undefined" ? scriptController : null
            ttsController: typeof ttsController !== "undefined" ? ttsController : null
            playbackController: typeof playbackController !== "undefined" ? playbackController : null
            voiceController: typeof voiceController !== "undefined" ? voiceController : null
            onNavigateRequested: function(page, workflow) { root.navigateRequested(page, workflow) }
            onToastRequested: function(message, variant) { root.toastRequested(message, variant) }
        }
    }


    Connections {
        target: typeof playbackController !== "undefined" ? playbackController : null
        ignoreUnknownSignals: true
        function onOperationFailed(message) { root.toastRequested(message, "error") }
        function onSelectedMediaChanged() {
            if (playbackController.selectedMediaId === "") root.selectedMediaId = ""
        }
    }

    FileDialog {
        id: importDialog
        title: "Import Media"
        fileMode: FileDialog.OpenFiles
        nameFilters: [
            "Media Files (*.mp4 *.mov *.mkv *.avi *.webm *.m4v *.mp3 *.wav *.m4a *.aac *.flac *.ogg *.opus *.jpg *.jpeg *.png *.webp *.bmp)",
            "Video Files (*.mp4 *.mov *.mkv *.avi *.webm *.m4v)",
            "Audio Files (*.mp3 *.wav *.m4a *.aac *.flac *.ogg *.opus)",
            "Images (*.jpg *.jpeg *.png *.webp *.bmp)",
            "All Files (*.*)"
        ]
        onAccepted: if (typeof mediaController !== "undefined") mediaController.importUrls(selectedFiles)
    }

    MediaDetailsDialog {
        id: detailsDialog
        onRevealRequested: function(mediaId) { if (typeof mediaController !== "undefined") mediaController.revealMedia(mediaId) }
        onRemoveRequested: function(mediaId, mediaName) { detailsDialog.close(); root.requestRemove(mediaId, mediaName) }
    }

    AppDialog {
        id: removeMediaDialog
        width: 470
        parent: Overlay.overlay
        x: (parent.width - width) / 2
        y: (parent.height - height) / 2
        header: null
        footer: null
        closePolicy: Popup.CloseOnEscape
        contentItem: ColumnLayout {
            spacing: Theme.spacing.lg
            Text { Layout.fillWidth: true; text: "Remove \"" + root.removeMediaName + "\" from this project?"; wrapMode: Text.WordWrap; color: Theme.colors.textPrimary; font.family: Theme.type.family; font.pixelSize: Theme.type.heading; font.weight: Theme.type.semibold }
            InfoBanner { Layout.fillWidth: true; text: "The project copy and its thumbnail will be deleted. Your original source file will not be changed."; variant: "info" }
            RowLayout {
                Layout.fillWidth: true
                Item { Layout.fillWidth: true }
                SecondaryButton { text: "Cancel"; onClicked: removeMediaDialog.close() }
                AppButton {
                    text: "Remove"
                    variant: "danger"
                    iconName: "trash"
                    onClicked: {
                        if (typeof mediaController !== "undefined" && mediaController.removeMedia(root.removeMediaId)) {
                            if (root.selectedMediaId === root.removeMediaId) root.selectedMediaId = ""
                            removeMediaDialog.close()
                        }
                    }
                }
            }
        }
    }

    AppDialog {
        id: renameDialog
        width: 440
        parent: Overlay.overlay
        x: (parent.width - width) / 2
        y: (parent.height - height) / 2
        header: null
        footer: null
        contentItem: ColumnLayout {
            spacing: Theme.spacing.lg
            Text { text: "Rename Project"; color: Theme.colors.textPrimary; font.family: Theme.type.family; font.pixelSize: Theme.type.heading; font.weight: Theme.type.semibold }
            AppTextField { id: renameField; Layout.fillWidth: true; maximumLength: 120 }
            RowLayout {
                Layout.fillWidth: true
                Item { Layout.fillWidth: true }
                SecondaryButton { text: "Cancel"; onClicked: renameDialog.close() }
                AppButton {
                    text: "Rename"
                    onClicked: {
                        if (renameField.text.trim().length === 0) { root.toastRequested("Project name cannot be empty.", "warning"); return }
                        if (typeof projectController !== "undefined" && projectController.renameProject(root.current().id, renameField.text.trim())) renameDialog.close()
                    }
                }
            }
        }
    }

    AppDialog {
        id: deleteDialog
        width: 470
        parent: Overlay.overlay
        x: (parent.width - width) / 2
        y: (parent.height - height) / 2
        header: null
        footer: null
        contentItem: ColumnLayout {
            spacing: Theme.spacing.lg
            Text { Layout.fillWidth: true; text: "Delete \"" + (root.current().title || "this project") + "\"?"; wrapMode: Text.WordWrap; color: Theme.colors.textPrimary; font.family: Theme.type.family; font.pixelSize: Theme.type.heading; font.weight: Theme.type.semibold }
            Text { Layout.fillWidth: true; text: "The project and its managed media copies will be permanently deleted. Original source files imported from outside the project will not be changed."; wrapMode: Text.WordWrap; color: Theme.colors.textSecondary; font.family: Theme.type.family; font.pixelSize: Theme.type.bodySmall }
            RowLayout {
                Layout.fillWidth: true
                Item { Layout.fillWidth: true }
                SecondaryButton { text: "Cancel"; onClicked: deleteDialog.close() }
                AppButton {
                    text: "Delete Project"; variant: "danger"; iconName: "trash"
                    onClicked: {
                        if (typeof scriptController !== "undefined" && !scriptController.flush()) return
                        if (typeof playbackController !== "undefined") playbackController.clear()
                        if (typeof projectController !== "undefined" && projectController.deleteProject(root.current().id)) {
                            deleteDialog.close()
                            root.navigateRequested("projects", "")
                        }
                    }
                }
            }
        }
    }
}
