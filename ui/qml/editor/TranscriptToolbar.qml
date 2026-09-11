import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15
import "../theme"
import "../components"

RowLayout {
    id: root
    property var controller
    signal exportRequested()
    spacing: Theme.spacing.sm

    AppTextField {
        Layout.preferredWidth: 240
        placeholderText: "Search transcript"
        onTextChanged: if (root.controller) root.controller.setSearch(text)
    }
    Item { Layout.fillWidth: true }
    Text {
        text: root.controller ? root.controller.saveState : "Saved"
        color: Theme.colors.textMuted
        font.family: Theme.type.family
        font.pixelSize: Theme.type.caption
    }
    SecondaryButton { text: "Copy Full Transcript"; compact: true; onClicked: if (root.controller) root.controller.copyFullTranscript() }
    SecondaryButton { text: "Export TXT"; compact: true; onClicked: root.exportRequested() }
}
