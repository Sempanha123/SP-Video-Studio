import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15
import "../theme"
RowLayout {
    id: root
    property string text: "Loading…"
    spacing: Theme.spacing.md
    Accessible.name: text
    BusyIndicator { running: true; Layout.preferredWidth: 24; Layout.preferredHeight: 24 }
    Text { text: root.text; color: Theme.colors.textSecondary; font.family: Theme.type.family; font.pixelSize: Theme.type.body }
}
