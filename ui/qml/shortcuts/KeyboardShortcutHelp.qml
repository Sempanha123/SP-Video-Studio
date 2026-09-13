import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15
import SPVideoStudio.Commands 1.0
import "../theme"
import "../components"

AppDialog {
    id: root
    width: Math.min(780, parent ? parent.width - 48 : 780)
    height: Math.min(650, parent ? parent.height - 64 : 650)
    header: null
    footer: null
    modal: true
    property var rows: []
    signal customizeRequested()

    function refresh() { rows = Shortcuts.search(search.text) }
    onOpened: { Commands.setModalOpen(true); refresh(); search.forceActiveFocus() }
    onClosed: Commands.setModalOpen(false)

    contentItem: ColumnLayout {
        spacing: Theme.spacing.md
        RowLayout {
            Layout.fillWidth: true
            ColumnLayout {
                Layout.fillWidth: true
                Text { text: "Keyboard Shortcuts"; color: Theme.colors.textPrimary; font.family: Theme.type.family; font.pixelSize: Theme.type.title; font.weight: Theme.type.semibold }
                Text { text: "Use the mouse normally; shortcuts are optional productivity helpers."; color: Theme.colors.textMuted; font.family: Theme.type.family; font.pixelSize: Theme.type.bodySmall }
            }
            IconButton { iconName: "close"; tooltip: "Close"; onClicked: root.close() }
        }
        AppTextField {
            id: search
            Layout.fillWidth: true
            placeholderText: "Search General, Playback, Timeline, Speech, Subtitles…"
            onTextChanged: root.refresh()
        }
        ListView {
            Layout.fillWidth: true
            Layout.fillHeight: true
            model: root.rows
            clip: true
            reuseItems: true
            delegate: Rectangle {
                required property var modelData
                width: ListView.view.width
                height: 44
                color: index % 2 ? Theme.colors.surfaceRaised : "transparent"
                RowLayout {
                    anchors.fill: parent
                    anchors.leftMargin: Theme.spacing.sm
                    anchors.rightMargin: Theme.spacing.sm
                    Text { Layout.preferredWidth: 130; text: modelData.category; color: Theme.colors.textMuted; font.family: Theme.type.family; font.pixelSize: Theme.type.caption }
                    Text { Layout.fillWidth: true; text: modelData.name; color: Theme.colors.textPrimary; font.family: Theme.type.family; font.pixelSize: Theme.type.bodySmall; elide: Text.ElideRight }
                    Text { Layout.preferredWidth: 150; horizontalAlignment: Text.AlignRight; text: modelData.shortcut || "—"; color: Theme.colors.textSecondary; font.family: Theme.type.family; font.pixelSize: Theme.type.bodySmall }
                }
            }
            ScrollBar.vertical: ScrollBar {}
        }
        SecondaryButton {
            text: "Customize Shortcuts"
            onClicked: { root.close(); root.customizeRequested() }
        }
    }
}
