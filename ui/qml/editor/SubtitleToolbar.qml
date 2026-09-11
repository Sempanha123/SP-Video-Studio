import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15
import "../theme"
import "../components"

RowLayout {
    id: root
    property var controller
    signal createRequested()
    signal importRequested()
    signal exportRequested()
    signal renderPreviewRequested()
    spacing: Theme.spacing.sm

    AppButton { text: "Create Track"; compact: true; onClicked: root.createRequested() }
    SecondaryButton { text: "Import"; compact: true; onClicked: root.importRequested() }
    SecondaryButton { text: "Export"; compact: true; enabled: !!root.controller && !!root.controller.track.id; onClicked: root.exportRequested() }
    SecondaryButton { text: "+ Cue"; compact: true; enabled: !!root.controller && !!root.controller.track.id; onClicked: root.controller.addCueAtPlayhead() }
    SecondaryButton { text: "Render Preview"; compact: true; enabled: !!root.controller && !!root.controller.track.id && !root.controller.busy; onClicked: root.renderPreviewRequested() }
    SecondaryButton { text: "Sync Source"; compact: true; visible: !!root.controller && root.controller.track.source_type !== "manual"; onClicked: root.controller.syncSource() }
    Item { Layout.fillWidth: true }
    Text { text: root.controller ? root.controller.saveState : "Saved"; color: Theme.colors.textMuted; font.family: Theme.type.family; font.pixelSize: Theme.type.caption }
}
