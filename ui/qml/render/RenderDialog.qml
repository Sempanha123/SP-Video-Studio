import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15
import "../theme"
import "../components"

Item {
    id: root
    property var controller
    property string aspectRatio: "16:9"
    property int projectFps: 30
    property var validationIssues: []
    signal toastRequested(string message, string variant)

    function validateSettings() {
        if (!controller) return
        validationIssues = controller.validate(settings.presetId, settings.renderWidth, settings.renderHeight, settings.renderFps, settings.encoder, settings.quality, settings.subtitleTrackId, settings.keepTemp)
    }
    function startRender() {
        validateSettings()
        for (var i=0;i<validationIssues.length;++i) {
            if (validationIssues[i].severity === "error") {
                root.toastRequested(validationIssues[i].message, "error")
                return
            }
        }
        controller.start(settings.presetId, settings.renderWidth, settings.renderHeight, settings.renderFps, settings.encoder, settings.quality, settings.subtitleTrackId, settings.keepTemp)
    }

    ScrollView {
        anchors.fill: parent
        clip: true
        contentWidth: availableWidth
        ColumnLayout {
            width: root.width
            spacing: Theme.spacing.lg

            RowLayout {
                Layout.fillWidth: true
                ColumnLayout { Layout.fillWidth: true; spacing: 2
                    Text { text: "Render Video"; color: Theme.colors.textPrimary; font.family: Theme.type.family; font.pixelSize: Theme.type.titleLarge; font.weight: Theme.type.semibold }
                    Text { text: "Create a validated MP4 from the current scene snapshot."; color: Theme.colors.textSecondary; font.family: Theme.type.family; font.pixelSize: Theme.type.bodySmall }
                }
                StatusBadge { text: root.controller && root.controller.busy ? "Rendering" : "Ready"; status: root.controller && root.controller.busy ? "processing" : "ready" }
            }

            RenderSettings {
                id: settings
                Layout.fillWidth: true
                controller: root.controller
                aspectRatio: root.aspectRatio
                projectFps: root.projectFps
                enabled: !root.controller || !root.controller.busy
                onValidateRequested: root.validateSettings()
                onRenderRequested: root.startRender()
                onSettingsChanged: root.validationIssues = []
            }

            AppCard {
                Layout.fillWidth: true
                visible: root.validationIssues.length > 0 && !(root.controller && root.controller.busy)
                implicitHeight: issueColumn.implicitHeight + Theme.spacing.lg * 2
                ColumnLayout {
                    id: issueColumn; anchors.fill: parent; anchors.margins: Theme.spacing.lg; spacing: Theme.spacing.sm
                    Text { text: "Pre-render Check"; color: Theme.colors.textPrimary; font.family: Theme.type.family; font.pixelSize: Theme.type.body; font.weight: Theme.type.semibold }
                    Repeater {
                        model: root.validationIssues
                        delegate: RowLayout {
                            required property var modelData
                            Layout.fillWidth: true
                            StatusBadge { text: modelData.severity === "error" ? "Error" : "Warning"; status: modelData.severity === "error" ? "invalid" : "warning" }
                            Text { Layout.fillWidth: true; text: modelData.message; wrapMode: Text.WordWrap; color: Theme.colors.textSecondary; font.family: Theme.type.family; font.pixelSize: Theme.type.bodySmall }
                        }
                    }
                }
            }

            RenderProgress { Layout.fillWidth: true; visible: root.controller && root.controller.busy; controller: root.controller }
            RenderResult { Layout.fillWidth: true; visible: root.controller && !!root.controller.lastOutput.id && !root.controller.busy; controller: root.controller }

            AppCard {
                Layout.fillWidth: true
                implicitHeight: Math.max(150, historyColumn.implicitHeight + Theme.spacing.lg * 2)
                ColumnLayout {
                    id: historyColumn; anchors.fill: parent; anchors.margins: Theme.spacing.lg; spacing: Theme.spacing.sm
                    RowLayout { Layout.fillWidth: true
                        SectionHeader { Layout.fillWidth: true; title: "Recent Renders"; subtitle: "Completed project outputs" }
                        SecondaryButton { text: "Refresh"; compact: true; onClicked: if (root.controller) root.controller.refresh() }
                    }
                    Text { visible: !root.controller || root.controller.history.length === 0; text: "No completed renders yet."; color: Theme.colors.textMuted; font.family: Theme.type.family; font.pixelSize: Theme.type.bodySmall }
                    Repeater {
                        model: root.controller ? root.controller.history.slice(0, 6) : []
                        delegate: Rectangle {
                            required property var modelData
                            Layout.fillWidth: true; implicitHeight: 54; radius: Theme.radius.medium; color: Theme.colors.surfaceHover; border.color: Theme.colors.border
                            RowLayout { anchors.fill: parent; anchors.margins: Theme.spacing.md; spacing: Theme.spacing.md
                                ColumnLayout { Layout.fillWidth: true; spacing: 1
                                    Text { Layout.fillWidth: true; text: modelData.name; elide: Text.ElideMiddle; color: Theme.colors.textPrimary; font.family: Theme.type.family; font.pixelSize: Theme.type.bodySmall; font.weight: Theme.type.semibold }
                                    Text { text: modelData.resolutionText + " • " + modelData.durationText + " • " + modelData.fileSizeText; color: Theme.colors.textMuted; font.family: Theme.type.family; font.pixelSize: Theme.type.caption }
                                }
                                SecondaryButton { text: "Play"; compact: true; onClicked: root.controller.playOutput(modelData.id) }
                                IconButton { iconName: "folder"; tooltip: "Open output folder"; onClicked: root.controller.openFolder(modelData.id) }
                            }
                        }
                    }
                }
            }
        }
    }

    Connections {
        target: root.controller
        ignoreUnknownSignals: true
        function onOperationSucceeded(message) { root.toastRequested(message, "success") }
        function onOperationFailed(message) { root.toastRequested(message, "error") }
    }
}
