import QtQuick 2.15
import QtQuick.Layouts 1.15
import "../theme"
Item {
    id: root
    property string iconName: "spark"
    property string title: "Nothing here yet"
    property string description: "Start by adding something to your project."
    property alias action: actionHost.data
    implicitWidth: 360; implicitHeight: 180
    ColumnLayout { anchors.centerIn: parent; width: Math.min(parent.width - 32, 360); spacing: Theme.spacing.sm
        Rectangle { Layout.alignment: Qt.AlignHCenter; width: 42; height: 42; radius: 12; color: Theme.colors.accentSoft; Icon { anchors.centerIn: parent; width: 19; height: 19; name: root.iconName } }
        Text { Layout.fillWidth: true; text: root.title; horizontalAlignment: Text.AlignHCenter; color: Theme.colors.textPrimary; font.family: Theme.type.family; font.pixelSize: Theme.type.sectionTitle; font.weight: Theme.type.semibold }
        Text { Layout.fillWidth: true; text: root.description; horizontalAlignment: Text.AlignHCenter; wrapMode: Text.WordWrap; color: Theme.colors.textSecondary; font.family: Theme.type.family; font.pixelSize: Theme.type.small }
        RowLayout { id: actionHost; Layout.alignment: Qt.AlignHCenter; Layout.topMargin: Theme.spacing.xs }
    }
}
