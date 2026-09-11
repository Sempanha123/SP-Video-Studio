import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15
import "../theme"
import "../components"

AppCard {
    id: root
    property var controller
    property string aspectRatio: "16:9"
    property int projectFps: 30
    property string presetId: ""
    property int renderWidth: 1920
    property int renderHeight: 1080
    property int renderFps: 30
    property string encoder: "auto"
    property string quality: "balanced"
    property string subtitleTrackId: ""
    property bool keepTemp: false
    signal settingsChanged()
    signal validateRequested()
    signal renderRequested()

    function applyPreset(index) {
        if (!controller || index < 0 || index >= controller.presets.length) return
        var p = controller.presets[index]
        presetId = p.id
        renderWidth = p.width
        renderHeight = p.height
        renderFps = projectFps > 0 ? projectFps : p.fps
        settingsChanged()
    }

    function chooseAspectPreset() {
        if (!controller || !controller.presets) return
        for (var i = 0; i < controller.presets.length; ++i) {
            if (controller.presets[i].metadata.aspectRatio === aspectRatio) {
                presetBox.currentIndex = i
                applyPreset(i)
                return
            }
        }
        if (controller.presets.length > 0) applyPreset(0)
    }

    Component.onCompleted: chooseAspectPreset()
    onControllerChanged: Qt.callLater(chooseAspectPreset)
    onAspectRatioChanged: Qt.callLater(chooseAspectPreset)

    ColumnLayout {
        anchors.fill: parent
        anchors.margins: Theme.spacing.lg
        spacing: Theme.spacing.md

        SectionHeader { title: "Render Settings"; subtitle: "Production MP4 output" }

        GridLayout {
            Layout.fillWidth: true
            columns: width < 620 ? 1 : 2
            columnSpacing: Theme.spacing.md
            rowSpacing: Theme.spacing.sm

            ColumnLayout {
                Layout.fillWidth: true
                Text { text: "Format"; color: Theme.colors.textSecondary; font.family: Theme.type.family; font.pixelSize: Theme.type.caption }
                AppComboBox {
                    id: presetBox
                    Layout.fillWidth: true
                    model: root.controller ? root.controller.presets : []
                    textRole: "name"
                    onActivated: root.applyPreset(currentIndex)
                }
            }
            ColumnLayout {
                Layout.fillWidth: true
                Text { text: "Resolution"; color: Theme.colors.textSecondary; font.family: Theme.type.family; font.pixelSize: Theme.type.caption }
                Text { text: root.renderWidth + " × " + root.renderHeight; color: Theme.colors.textPrimary; font.family: Theme.type.family; font.pixelSize: Theme.type.body; Layout.minimumHeight: 38; verticalAlignment: Text.AlignVCenter }
            }
            ColumnLayout {
                Layout.fillWidth: true
                Text { text: "FPS"; color: Theme.colors.textSecondary; font.family: Theme.type.family; font.pixelSize: Theme.type.caption }
                AppComboBox {
                    Layout.fillWidth: true
                    model: [24,25,30,50,60]
                    Component.onCompleted: currentIndex = Math.max(0, model.indexOf(root.renderFps))
                    onActivated: { root.renderFps = Number(currentText); root.settingsChanged() }
                }
            }
            ColumnLayout {
                Layout.fillWidth: true
                Text { text: "Encoder"; color: Theme.colors.textSecondary; font.family: Theme.type.family; font.pixelSize: Theme.type.caption }
                AppComboBox {
                    id: encoderBox
                    Layout.fillWidth: true
                    model: {
                        var out=[{"id":"auto","name":"Auto"}]
                        if (!root.controller) return out
                        var seen={"auto":true}
                        for (var i=0;i<root.controller.encoderOptions.length;++i) {
                            var e=root.controller.encoderOptions[i]
                            if (!seen[e.id] && e.available) { out.push(e); seen[e.id]=true }
                        }
                        return out
                    }
                    textRole: "name"; valueRole: "id"
                    onActivated: { root.encoder = currentValue || "auto"; root.settingsChanged() }
                }
            }
            ColumnLayout {
                Layout.fillWidth: true
                Text { text: "Quality"; color: Theme.colors.textSecondary; font.family: Theme.type.family; font.pixelSize: Theme.type.caption }
                AppComboBox {
                    Layout.fillWidth: true
                    model: [{"id":"fast","name":"Fast"},{"id":"balanced","name":"Balanced"},{"id":"high","name":"High Quality"}]
                    textRole: "name"; valueRole: "id"; currentIndex: 1
                    onActivated: { root.quality = currentValue || "balanced"; root.settingsChanged() }
                }
            }
            ColumnLayout {
                Layout.fillWidth: true
                Text { text: "Subtitles"; color: Theme.colors.textSecondary; font.family: Theme.type.family; font.pixelSize: Theme.type.caption }
                AppComboBox {
                    id: subtitleBox
                    Layout.fillWidth: true
                    model: {
                        var rows=[{"id":"","name":"None"}]
                        if (!root.controller) return rows
                        for (var i=0;i<root.controller.subtitleTracks.length;++i) rows.push(root.controller.subtitleTracks[i])
                        return rows
                    }
                    textRole: "name"; valueRole: "id"
                    onActivated: { root.subtitleTrackId = currentValue || ""; root.settingsChanged() }
                }
            }
        }

        RowLayout {
            Layout.fillWidth: true
            AppSwitch { checked: root.keepTemp; onToggled: { root.keepTemp = checked; root.settingsChanged() } }
            Text { text: "Keep temporary render files"; color: Theme.colors.textSecondary; font.family: Theme.type.family; font.pixelSize: Theme.type.bodySmall }
            Item { Layout.fillWidth: true }
            SecondaryButton { text: "Validate"; compact: true; enabled: !root.controller || !root.controller.busy; onClicked: root.validateRequested() }
            AppButton { text: "Render Video"; compact: true; enabled: root.controller && !root.controller.busy; onClicked: root.renderRequested() }
        }
    }
}
