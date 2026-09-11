import QtQuick 2.15
import QtQuick.Layouts 1.15
import "../theme"
import "../components"

Item {
    ColumnLayout { anchors.fill: parent; spacing: Theme.spacing.xl
        ColumnLayout { Layout.fillWidth: true; spacing: 2
            Text { text: "Batch Factory"; color: Theme.colors.textPrimary; font.family: Theme.type.family; font.pixelSize: Theme.type.titleLarge; font.weight: Theme.type.semibold }
            Text { text: "Prepare repeatable video creation workflows for larger content runs."; color: Theme.colors.textSecondary; font.family: Theme.type.family; font.pixelSize: Theme.type.body }
        }
        AppCard { Layout.fillWidth: true; Layout.fillHeight: true; EmptyState { anchors.centerIn: parent; title: "Batch workspace is ready for a future phase"; description: "Batch Factory will allow multiple videos to be queued and generated from reusable templates."; iconName: "batch" } }
    }
}
